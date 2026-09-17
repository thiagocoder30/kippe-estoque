"""
NF-001J.8 — Safe Receiving Execution.

Application orchestration boundary between deterministic receiving
identity and the existing quantitative receiving domain.

This service does not replace ReceivingEngine. It coordinates
idempotency with the repository's atomic persistence authority.
"""

from dataclasses import dataclass
from typing import Optional

from src.application.procurement.receiving_identity import (
    ReceivingIdentityEnvelope,
    ReceivingReplayDecision,
    ReceivingReplayStatus,
)
from src.domain.services.receiving_engine import (
    ReceivingEngine,
)


@dataclass(frozen=True)
class SafeReceivingExecutionResult:
    decision: ReceivingReplayDecision
    receiving_result: Optional[object]
    operation_status: Optional[str]
    audit_event_id: Optional[int]

    @property
    def executed(self) -> bool:
        return (
            self.decision.status
            == ReceivingReplayStatus.NEW
            and self.operation_status
            == "COMPLETED"
        )


class SafeReceivingExecutionService:
    """
    Executes one deterministic receiving operation at most once.
    """

    @classmethod
    def execute(
        cls,
        repository,
        envelope: ReceivingIdentityEnvelope,
        *,
        identifier: str,
        quantity: int,
        batch_code: str,
        expiration_date: str,
        supplier: str,
        manufacturing_date: str,
        invoice_id: str,
        operator_id: str,
    ) -> SafeReceivingExecutionResult:

        if not isinstance(
            envelope,
            ReceivingIdentityEnvelope,
        ):
            raise TypeError(
                "Safe receiving execution requires "
                "ReceivingIdentityEnvelope."
            )

        existing = repository.get_receiving_operation(
            envelope.idempotency_key
        )

        if existing is not None:
            if (
                existing["fingerprint"]
                == envelope.fingerprint
            ):
                status = ReceivingReplayStatus.REPLAY
            else:
                status = ReceivingReplayStatus.CONFLICT

            decision = ReceivingReplayDecision(
                status=status,
                identity=envelope.identity,
                current_fingerprint=(
                    envelope.fingerprint
                ),
                previous_fingerprint=(
                    existing["fingerprint"]
                ),
            )

            return SafeReceivingExecutionResult(
                decision=decision,
                receiving_result=None,
                operation_status=existing["status"],
                audit_event_id=None,
            )

        products = repository.get_all()

        quantity_before_by_product = {
            product.id: product.quantity
            for product in products
        }

        receiving_result = ReceivingEngine.receive(
            products=products,
            identifier=identifier,
            quantity=quantity,
            batch_code=batch_code,
            expiration_date=expiration_date,
            supplier=supplier,
            manufacturing_date=manufacturing_date,
        )

        if not receiving_result.is_success:
            decision = ReceivingReplayDecision(
                status=ReceivingReplayStatus.NEW,
                identity=envelope.identity,
                current_fingerprint=(
                    envelope.fingerprint
                ),
                previous_fingerprint=None,
            )

            return SafeReceivingExecutionResult(
                decision=decision,
                receiving_result=receiving_result,
                operation_status=None,
                audit_event_id=None,
            )

        product_id = receiving_result.value[
            "product_id"
        ]

        product = next(
            product
            for product in products
            if product.id == product_id
        )

        quantity_before = (
            quantity_before_by_product[
                product_id
            ]
        )

        persistence = (
            repository.save_claimed_receiving_with_operational_audit(
                product,
                idempotency_key=(
                    envelope.idempotency_key
                ),
                fingerprint=envelope.fingerprint,
                origin_document=(
                    envelope.identity.origin_document
                ),
                supplier_id=(
                    envelope.identity.supplier_id
                ),
                invoice_number=(
                    envelope.identity.invoice_number
                ),
                line_number=(
                    envelope.identity.line_number
                ),
                event_type="RECEBIMENTO",
                product_id=product_id,
                batch_code=receiving_result.value[
                    "batch_code"
                ],
                location_id="",
                quantity_planned=None,
                quantity_actual=receiving_result.value[
                    "quantity"
                ],
                quantity_before=quantity_before,
                quantity_after=product.quantity,
                quantity_divergence=None,
                supplier=receiving_result.value[
                    "supplier"
                ],
                document_id=invoice_id,
                operator_id=operator_id,
                metadata={
                    "manufacturing_date": (
                        receiving_result.value[
                            "manufacturing_date"
                        ]
                    ),
                    "expiration_date": (
                        receiving_result.value[
                            "expiration_date"
                        ]
                    ),
                },
            )
        )

        status = ReceivingReplayStatus(
            persistence["status"]
        )

        decision = ReceivingReplayDecision(
            status=status,
            identity=envelope.identity,
            current_fingerprint=(
                persistence[
                    "current_fingerprint"
                ]
            ),
            previous_fingerprint=(
                persistence[
                    "previous_fingerprint"
                ]
            ),
        )

        if status != ReceivingReplayStatus.NEW:
            receiving_result = None

        return SafeReceivingExecutionResult(
            decision=decision,
            receiving_result=receiving_result,
            operation_status=persistence[
                "operation_status"
            ],
            audit_event_id=persistence[
                "audit_event_id"
            ],
        )
