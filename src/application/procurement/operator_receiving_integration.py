"""
NF-001J.9 — Operator Receiving Integration Boundary.

Canonical application orchestration from an already reconciled supplier
invoice through explicit human physical conference and the certified
J.3 -> J.8 receiving pipeline.

This service deliberately does NOT:
- parse HTTP;
- access Flask/session;
- execute SQL;
- create products;
- resolve NEEDS_REGISTRATION lines;
- replace ReceivingEngine;
- bypass J.8.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from src.application.procurement.invoice_conference import (
    InvoiceConferenceService,
)
from src.application.procurement.receiving_preparation import (
    ReceivingPreparationService,
)
from src.application.procurement.stockist_handoff import (
    StockistHandoffService,
    StockistHandoffStatus,
)
from src.application.procurement.receiving_adapter import (
    ReceivingAdapter,
)
from src.application.procurement.receiving_identity import (
    ReceivingIdentityService,
)
from src.application.procurement.receiving_execution import (
    SafeReceivingExecutionService,
)


@dataclass(frozen=True)
class OperatorReceivingLineResult:
    line_number: int
    product_id: str
    status: str
    executed: bool
    operation_status: Optional[str]
    audit_event_id: Optional[int]


@dataclass(frozen=True)
class OperatorReceivingIntegrationResult:
    invoice_number: str
    supplier_id: str
    conference_closed_by: str
    total_lines: int
    divergent_lines: int
    executed_lines: int
    replay_lines: int
    skipped_zero_quantity_lines: int
    lines: List[OperatorReceivingLineResult]


class OperatorReceivingIntegrationService:
    """
    NF-001J.9 canonical application orchestration.

    The operator explicitly supplies:
    - physical count for every reconciled line;
    - lot/expiration/manufacturing data for actionable lines.

    Inventory mutation remains exclusively under J.8.
    """

    @classmethod
    def execute(
        cls,
        *,
        repository,
        reconciliation,
        operator_id: str,
        counts: Dict[int, int],
        physical_data: Dict[int, Dict[str, str]],
    ) -> OperatorReceivingIntegrationResult:

        normalized_operator = str(
            operator_id or ""
        ).strip()

        if not normalized_operator:
            raise ValueError(
                "Operador da conferência é obrigatório."
            )

        if not isinstance(counts, dict):
            raise TypeError(
                "counts deve ser um mapa por line_number."
            )

        if not isinstance(physical_data, dict):
            raise TypeError(
                "physical_data deve ser um mapa por line_number."
            )

        conference = InvoiceConferenceService.open(
            reconciliation,
            normalized_operator,
        )

        # BLOCKED_REGISTRATION is enforced by ConferenceSession.close().
        # Every non-blocked line must receive an explicit human count.
        for line in conference.lines:
            if getattr(
                line.status,
                "value",
                str(line.status),
            ) == "BLOCKED_REGISTRATION":
                continue

            if line.line_number not in counts:
                raise ValueError(
                    "Quantidade física ausente para linha "
                    f"{line.line_number}."
                )

            conference.register_count(
                line_number=line.line_number,
                quantity=counts[line.line_number],
                operator_id=normalized_operator,
            )

        closed = InvoiceConferenceService.close(
            conference,
            normalized_operator,
        )

        preparation = ReceivingPreparationService.prepare(
            closed
        )

        for line in preparation.lines:
            if line.quantity_to_receive == 0:
                continue

            data = physical_data.get(
                line.line_number
            )

            if not isinstance(data, dict):
                raise ValueError(
                    "Dados físicos ausentes para linha "
                    f"{line.line_number}."
                )

            line.complete_physical_data(
                batch_code=data.get(
                    "batch_code",
                    "",
                ),
                expiration_date=data.get(
                    "expiration_date",
                    "",
                ),
                manufacturing_date=data.get(
                    "manufacturing_date",
                ),
            )

        handoff = StockistHandoffService.build(
            preparation,
            completed_by=normalized_operator,
        )

        results = []

        for line in handoff.lines:
            if (
                line.status
                == StockistHandoffStatus.SKIPPED_ZERO_QUANTITY
            ):
                results.append(
                    OperatorReceivingLineResult(
                        line_number=line.line_number,
                        product_id=line.product_id,
                        status="SKIPPED_ZERO_QUANTITY",
                        executed=False,
                        operation_status=None,
                        audit_event_id=None,
                    )
                )
                continue

            if (
                line.status
                != StockistHandoffStatus.READY_FOR_RECEIVING
            ):
                raise ValueError(
                    "Linha não está pronta para recebimento: "
                    f"{line.line_number}."
                )

            command = ReceivingAdapter.build_line_command(
                handoff,
                line,
            )

            envelope = ReceivingIdentityService.build(
                handoff,
                line_number=line.line_number,
                command=command,
            )

            execution = SafeReceivingExecutionService.execute(
                repository,
                envelope,
                identifier=command.identifier,
                quantity=command.quantity,
                batch_code=command.batch_code,
                expiration_date=command.expiration_date,
                supplier=command.supplier,
                manufacturing_date=(
                    command.manufacturing_date
                ),
                invoice_id=command.invoice_id,
                operator_id=command.operator_id,
            )

            results.append(
                OperatorReceivingLineResult(
                    line_number=line.line_number,
                    product_id=line.product_id,
                    status=execution.decision.status.value,
                    executed=execution.executed,
                    operation_status=(
                        execution.operation_status
                    ),
                    audit_event_id=(
                        execution.audit_event_id
                    ),
                )
            )

        return OperatorReceivingIntegrationResult(
            invoice_number=handoff.invoice_number,
            supplier_id=handoff.supplier_id,
            conference_closed_by=(
                handoff.conference_closed_by
            ),
            total_lines=len(results),
            divergent_lines=closed.divergent_lines,
            executed_lines=sum(
                1
                for item in results
                if item.executed
            ),
            replay_lines=sum(
                1
                for item in results
                if item.status == "REPLAY"
            ),
            skipped_zero_quantity_lines=sum(
                1
                for item in results
                if item.status
                == "SKIPPED_ZERO_QUANTITY"
            ),
            lines=results,
        )
