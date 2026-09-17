"""
NF-001J — Explicit physical conference of reconciled supplier invoices.

This boundary exists after documentary preparation and catalog reconciliation.

It deliberately does not:
- parse or extract fiscal documents;
- duplicate SupplierInvoice fiscal master data;
- create products;
- perform product onboarding;
- reconcile catalog identities;
- persist conference sessions;
- receive goods;
- create batches;
- mutate inventory;
- perform putaway.

SupplierInvoice remains the fiscal authority.
CatalogReconciliationResult remains the catalog-identity authority.
The conference records only human physical-count evidence and its deterministic
comparison with the fiscal quantity.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from src.application.procurement.invoice_reconciliation import (
    CatalogReconciliationResult,
    ReconciliationStatus,
)


class ConferenceStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ConferenceLineStatus(str, Enum):
    PENDING_COUNT = "PENDING_COUNT"
    COUNTED = "COUNTED"
    BLOCKED_REGISTRATION = "BLOCKED_REGISTRATION"


@dataclass
class ConferenceLine:
    """
    Physical-conference state for one reconciled fiscal line.

    Fiscal evidence is referenced through reconciled_line rather than copied
    into a second fiscal model.
    """

    line_number: int
    reconciled_line: object
    counted_quantity: Optional[int] = None
    counted_by: str = ""

    @property
    def fiscal_line(self):
        return self.reconciled_line.invoice_line

    @property
    def product_id(self) -> str:
        return str(
            getattr(
                self.reconciled_line,
                "product_id",
                "",
            )
            or ""
        ).strip()

    @property
    def fiscal_quantity(self) -> int:
        return int(self.fiscal_line.quantity)

    @property
    def reconciliation_status(self):
        return self.reconciled_line.status

    @property
    def status(self) -> ConferenceLineStatus:
        if (
            self.reconciliation_status
            == ReconciliationStatus.NEEDS_REGISTRATION
        ):
            return ConferenceLineStatus.BLOCKED_REGISTRATION

        if self.counted_quantity is None:
            return ConferenceLineStatus.PENDING_COUNT

        return ConferenceLineStatus.COUNTED

    @property
    def divergence(self) -> Optional[int]:
        if self.counted_quantity is None:
            return None

        return self.counted_quantity - self.fiscal_quantity

    @property
    def is_divergent(self) -> bool:
        return (
            self.divergence is not None
            and self.divergence != 0
        )

    @property
    def can_count(self) -> bool:
        return (
            self.reconciliation_status
            == ReconciliationStatus.MATCHED
            and bool(self.product_id)
        )

    def register_count(
        self,
        quantity: int,
        operator_id: str,
    ) -> None:
        if not self.can_count:
            raise ValueError(
                "Linha bloqueada: produto requer cadastro "
                "e reconciliação antes da conferência física."
            )

        if self.counted_quantity is not None:
            raise ValueError(
                "A linha fiscal já possui contagem registrada."
            )

        if isinstance(quantity, bool):
            raise ValueError(
                "A quantidade conferida deve ser um inteiro "
                "maior ou igual a zero."
            )

        try:
            normalized_quantity = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(
                "A quantidade conferida deve ser um inteiro "
                "maior ou igual a zero."
            )

        if normalized_quantity != quantity:
            raise ValueError(
                "A quantidade conferida deve ser um inteiro "
                "maior ou igual a zero."
            )

        if normalized_quantity < 0:
            raise ValueError(
                "A quantidade conferida não pode ser negativa."
            )

        normalized_operator = str(
            operator_id or ""
        ).strip()

        if not normalized_operator:
            raise ValueError(
                "O operador da conferência é obrigatório."
            )

        self.counted_quantity = normalized_quantity
        self.counted_by = normalized_operator


@dataclass
class ConferenceSession:
    """
    Explicit physical conference session for one reconciliation result.

    The session owns only physical-count workflow state.
    It does not own fiscal evidence, catalog identity or inventory mutation.
    """

    reconciliation: CatalogReconciliationResult
    opened_by: str
    lines: List[ConferenceLine] = field(
        init=False
    )
    status: ConferenceStatus = field(
        default=ConferenceStatus.OPEN,
        init=False,
    )
    closed_by: str = field(
        default="",
        init=False,
    )

    def __post_init__(self):
        normalized_operator = str(
            self.opened_by or ""
        ).strip()

        if not normalized_operator:
            raise ValueError(
                "O operador que abriu a conferência é obrigatório."
            )

        self.opened_by = normalized_operator

        self.lines = [
            ConferenceLine(
                line_number=index,
                reconciled_line=reconciled_line,
            )
            for index, reconciled_line in enumerate(
                self.reconciliation.lines,
                start=1,
            )
        ]

    @property
    def invoice(self):
        return self.reconciliation.invoice

    @property
    def invoice_number(self) -> str:
        return self.invoice.invoice_number

    @property
    def supplier_id(self) -> str:
        return self.invoice.supplier_id

    @property
    def total_lines(self) -> int:
        return len(self.lines)

    @property
    def counted_lines(self) -> int:
        return sum(
            1
            for line in self.lines
            if line.status == ConferenceLineStatus.COUNTED
        )

    @property
    def blocked_lines(self) -> int:
        return sum(
            1
            for line in self.lines
            if (
                line.status
                == ConferenceLineStatus.BLOCKED_REGISTRATION
            )
        )

    @property
    def divergent_lines(self) -> int:
        return sum(
            1
            for line in self.lines
            if line.is_divergent
        )

    @property
    def is_closed(self) -> bool:
        return self.status == ConferenceStatus.CLOSED

    @property
    def can_close(self) -> bool:
        return (
            self.status == ConferenceStatus.OPEN
            and self.total_lines > 0
            and self.blocked_lines == 0
            and self.counted_lines == self.total_lines
        )

    def _require_open(self) -> None:
        if self.status != ConferenceStatus.OPEN:
            raise ValueError(
                "A conferência já foi encerrada."
            )

    def get_line(
        self,
        line_number: int,
    ) -> ConferenceLine:
        for line in self.lines:
            if line.line_number == line_number:
                return line

        raise ValueError(
            f"Linha de conferência inexistente: {line_number}."
        )

    def register_count(
        self,
        line_number: int,
        quantity: int,
        operator_id: str,
    ) -> ConferenceLine:
        self._require_open()

        line = self.get_line(line_number)

        line.register_count(
            quantity=quantity,
            operator_id=operator_id,
        )

        return line

    def close(
        self,
        operator_id: str,
    ) -> None:
        self._require_open()

        normalized_operator = str(
            operator_id or ""
        ).strip()

        if not normalized_operator:
            raise ValueError(
                "O operador que encerra a conferência é obrigatório."
            )

        if self.blocked_lines:
            raise ValueError(
                "A conferência possui produtos pendentes de cadastro "
                "e reconciliação."
            )

        if self.counted_lines != self.total_lines:
            raise ValueError(
                "Todas as linhas conciliadas devem ser conferidas "
                "antes do encerramento."
            )

        if not self.lines:
            raise ValueError(
                "Não é possível encerrar uma conferência sem itens."
            )

        self.status = ConferenceStatus.CLOSED
        self.closed_by = normalized_operator


@dataclass(frozen=True)
class ConferenceLineResult:
    line_number: int
    product_id: str
    fiscal_quantity: int
    counted_quantity: int
    divergence: int
    counted_by: str


@dataclass(frozen=True)
class ConferenceClosedResult:
    """
    Immutable evidence emitted after explicit human closure.

    This is evidence for a future handoff boundary. It is not a receiving
    command and has no inventory authority.
    """

    invoice_number: str
    supplier_id: str
    closed_by: str
    lines: List[ConferenceLineResult]

    @property
    def total_lines(self) -> int:
        return len(self.lines)

    @property
    def divergent_lines(self) -> int:
        return sum(
            1
            for line in self.lines
            if line.divergence != 0
        )


class InvoiceConferenceService:
    """
    Application boundary for opening, counting and explicitly closing
    physical conference sessions.

    No repository or inventory authority is accepted as a dependency.
    """

    @staticmethod
    def open(
        reconciliation: CatalogReconciliationResult,
        operator_id: str,
    ) -> ConferenceSession:
        return ConferenceSession(
            reconciliation=reconciliation,
            opened_by=operator_id,
        )

    @staticmethod
    def close(
        session: ConferenceSession,
        operator_id: str,
    ) -> ConferenceClosedResult:
        session.close(operator_id)

        return ConferenceClosedResult(
            invoice_number=session.invoice_number,
            supplier_id=session.supplier_id,
            closed_by=session.closed_by,
            lines=[
                ConferenceLineResult(
                    line_number=line.line_number,
                    product_id=line.product_id,
                    fiscal_quantity=line.fiscal_quantity,
                    counted_quantity=int(
                        line.counted_quantity
                    ),
                    divergence=int(line.divergence),
                    counted_by=line.counted_by,
                )
                for line in session.lines
            ],
        )
