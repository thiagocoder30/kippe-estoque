"""
NF-001J.3 — Post-conference receiving preparation.

This boundary transforms immutable ConferenceClosedResult evidence into
human-completable receiving preparation.

It deliberately does not:
- persist tasks;
- create products;
- create batches;
- receive goods;
- mutate inventory;
- perform putaway;
- invent lot or expiration information.

The physically counted quantity is authoritative for receiving preparation.
Fiscal quantity and divergence remain preserved as evidence.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from src.application.procurement.invoice_conference import (
    ConferenceClosedResult,
    ConferenceLineResult,
)


class ReceivingPreparationStatus(str, Enum):
    NEEDS_COMPLETION = "NEEDS_COMPLETION"
    READY = "READY"
    SKIPPED_ZERO_QUANTITY = "SKIPPED_ZERO_QUANTITY"


@dataclass
class ReceivingPreparationLine:
    line_number: int
    product_id: str

    fiscal_quantity: int
    quantity_to_receive: int
    divergence: int

    counted_by: str

    batch_code: str = ""
    expiration_date: Optional[str] = None
    manufacturing_date: Optional[str] = None

    @property
    def status(self) -> ReceivingPreparationStatus:
        if self.quantity_to_receive == 0:
            return ReceivingPreparationStatus.SKIPPED_ZERO_QUANTITY

        if not self.batch_code.strip():
            return ReceivingPreparationStatus.NEEDS_COMPLETION

        if not self.expiration_date:
            return ReceivingPreparationStatus.NEEDS_COMPLETION

        return ReceivingPreparationStatus.READY

    @property
    def is_ready(self) -> bool:
        return self.status == ReceivingPreparationStatus.READY

    @property
    def requires_human_completion(self) -> bool:
        return self.status == ReceivingPreparationStatus.NEEDS_COMPLETION

    @property
    def is_zero_quantity(self) -> bool:
        return (
            self.status
            == ReceivingPreparationStatus.SKIPPED_ZERO_QUANTITY
        )

    def complete_physical_data(
        self,
        *,
        batch_code: str,
        expiration_date: str,
        manufacturing_date: Optional[str] = None,
    ) -> None:
        if self.quantity_to_receive == 0:
            raise ValueError(
                "Linha com quantidade física zero não requer "
                "preparação para recebimento."
            )

        normalized_batch = str(batch_code or "").strip()
        normalized_expiration = str(expiration_date or "").strip()

        if not normalized_batch:
            raise ValueError(
                "O lote é obrigatório para preparar o recebimento."
            )

        if not normalized_expiration:
            raise ValueError(
                "A validade é obrigatória para preparar o recebimento."
            )

        normalized_manufacturing = None

        if manufacturing_date is not None:
            candidate = str(manufacturing_date).strip()
            if candidate:
                normalized_manufacturing = candidate

        self.batch_code = normalized_batch
        self.expiration_date = normalized_expiration
        self.manufacturing_date = normalized_manufacturing


@dataclass
class ReceivingPreparationResult:
    invoice_number: str
    supplier_id: str
    conference_closed_by: str
    lines: List[ReceivingPreparationLine]

    @property
    def total_lines(self) -> int:
        return len(self.lines)

    @property
    def ready_lines(self) -> int:
        return sum(
            1
            for line in self.lines
            if line.status == ReceivingPreparationStatus.READY
        )

    @property
    def pending_lines(self) -> int:
        return sum(
            1
            for line in self.lines
            if (
                line.status
                == ReceivingPreparationStatus.NEEDS_COMPLETION
            )
        )

    @property
    def zero_quantity_lines(self) -> int:
        return sum(
            1
            for line in self.lines
            if (
                line.status
                == ReceivingPreparationStatus.SKIPPED_ZERO_QUANTITY
            )
        )

    @property
    def is_ready(self) -> bool:
        actionable = [
            line
            for line in self.lines
            if not line.is_zero_quantity
        ]

        return (
            bool(self.lines)
            and self.pending_lines == 0
            and all(line.is_ready for line in actionable)
        )

    def get_line(
        self,
        line_number: int,
    ) -> ReceivingPreparationLine:
        for line in self.lines:
            if line.line_number == line_number:
                return line

        raise ValueError(
            f"Linha de preparação inexistente: {line_number}."
        )


class ReceivingPreparationService:
    """
    Pure application transformer.

    Input:
        ConferenceClosedResult

    Output:
        ReceivingPreparationResult

    No receiving, persistence, batch or inventory dependency is accepted.
    """

    @staticmethod
    def prepare(
        conference: ConferenceClosedResult,
    ) -> ReceivingPreparationResult:
        if not isinstance(
            conference,
            ConferenceClosedResult,
        ):
            raise TypeError(
                "Receiving preparation requires "
                "ConferenceClosedResult."
            )

        lines = [
            ReceivingPreparationService._prepare_line(line)
            for line in conference.lines
        ]

        return ReceivingPreparationResult(
            invoice_number=conference.invoice_number,
            supplier_id=conference.supplier_id,
            conference_closed_by=conference.closed_by,
            lines=lines,
        )

    @staticmethod
    def _prepare_line(
        line: ConferenceLineResult,
    ) -> ReceivingPreparationLine:
        quantity = int(line.counted_quantity)

        if quantity < 0:
            raise ValueError(
                "Quantidade conferida negativa não pode ser "
                "preparada para recebimento."
            )

        return ReceivingPreparationLine(
            line_number=line.line_number,
            product_id=line.product_id,
            fiscal_quantity=int(line.fiscal_quantity),
            quantity_to_receive=quantity,
            divergence=int(line.divergence),
            counted_by=line.counted_by,
        )
