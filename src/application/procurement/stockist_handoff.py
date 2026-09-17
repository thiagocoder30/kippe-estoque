"""
NF-001J.4 — Stockist Handoff Contract

Pure application contract between receiving preparation and the future
receiving execution boundary.

This slice does NOT:
- persist tasks;
- expose HTTP;
- mutate stock;
- perform receiving;
- create batches;
- perform putaway;
- change conference evidence;
- introduce RBAC roles.

It only converts ReceivingPreparationResult into an explicit handoff
describing which lines still require physical completion, which lines are
ready for the existing receiving authority, and which zero-quantity lines
must be skipped.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from src.application.procurement.receiving_preparation import (
    ReceivingPreparationLine,
    ReceivingPreparationResult,
    ReceivingPreparationStatus,
)


class StockistHandoffStatus(str, Enum):
    PENDING_PHYSICAL_DATA = "PENDING_PHYSICAL_DATA"
    READY_FOR_RECEIVING = "READY_FOR_RECEIVING"
    SKIPPED_ZERO_QUANTITY = "SKIPPED_ZERO_QUANTITY"


@dataclass(frozen=True)
class StockistHandoffLine:
    line_number: int
    product_id: str

    fiscal_quantity: int
    quantity_to_receive: int
    divergence: int

    counted_by: str

    batch_code: str
    expiration_date: Optional[str]
    manufacturing_date: Optional[str]

    status: StockistHandoffStatus
    completed_by: Optional[str] = None

    @property
    def is_ready_for_receiving(self) -> bool:
        return (
            self.status
            == StockistHandoffStatus.READY_FOR_RECEIVING
        )

    @property
    def requires_physical_completion(self) -> bool:
        return (
            self.status
            == StockistHandoffStatus.PENDING_PHYSICAL_DATA
        )

    @property
    def is_zero_quantity(self) -> bool:
        return (
            self.status
            == StockistHandoffStatus.SKIPPED_ZERO_QUANTITY
        )


@dataclass(frozen=True)
class StockistHandoffResult:
    invoice_number: str
    supplier_id: str
    conference_closed_by: str
    lines: List[StockistHandoffLine]

    @property
    def total_lines(self) -> int:
        return len(self.lines)

    @property
    def ready_lines(self) -> int:
        return sum(
            1
            for line in self.lines
            if line.is_ready_for_receiving
        )

    @property
    def pending_lines(self) -> int:
        return sum(
            1
            for line in self.lines
            if line.requires_physical_completion
        )

    @property
    def zero_quantity_lines(self) -> int:
        return sum(
            1
            for line in self.lines
            if line.is_zero_quantity
        )

    @property
    def is_ready_for_receiving(self) -> bool:
        actionable = [
            line
            for line in self.lines
            if not line.is_zero_quantity
        ]

        return (
            bool(actionable)
            and self.pending_lines == 0
            and all(
                line.is_ready_for_receiving
                for line in actionable
            )
        )

    def get_line(
        self,
        line_number: int,
    ) -> StockistHandoffLine:
        for line in self.lines:
            if line.line_number == line_number:
                return line

        raise ValueError(
            f"Linha de handoff inexistente: {line_number}."
        )


class StockistHandoffService:
    """
    Pure transformer.

    Input:
        ReceivingPreparationResult

    Output:
        StockistHandoffResult

    The service does not execute receiving or persist workflow state.
    """

    @staticmethod
    def build(
        preparation: ReceivingPreparationResult,
        *,
        completed_by: Optional[str] = None,
    ) -> StockistHandoffResult:
        if not isinstance(
            preparation,
            ReceivingPreparationResult,
        ):
            raise TypeError(
                "Stockist handoff requires "
                "ReceivingPreparationResult."
            )

        normalized_completed_by = (
            StockistHandoffService
            ._normalize_operator(completed_by)
        )

        lines = [
            StockistHandoffService._build_line(
                line,
                completed_by=normalized_completed_by,
            )
            for line in preparation.lines
        ]

        return StockistHandoffResult(
            invoice_number=preparation.invoice_number,
            supplier_id=preparation.supplier_id,
            conference_closed_by=(
                preparation.conference_closed_by
            ),
            lines=lines,
        )

    @staticmethod
    def _normalize_operator(
        completed_by: Optional[str],
    ) -> Optional[str]:
        if completed_by is None:
            return None

        normalized = str(completed_by).strip()

        if not normalized:
            return None

        return normalized

    @staticmethod
    def _build_line(
        line: ReceivingPreparationLine,
        *,
        completed_by: Optional[str],
    ) -> StockistHandoffLine:
        if not isinstance(
            line,
            ReceivingPreparationLine,
        ):
            raise TypeError(
                "Stockist handoff line requires "
                "ReceivingPreparationLine."
            )

        if (
            line.status
            == ReceivingPreparationStatus.SKIPPED_ZERO_QUANTITY
        ):
            status = (
                StockistHandoffStatus.SKIPPED_ZERO_QUANTITY
            )
            line_completed_by = None

        elif (
            line.status
            == ReceivingPreparationStatus.READY
        ):
            status = (
                StockistHandoffStatus.READY_FOR_RECEIVING
            )
            line_completed_by = completed_by

        else:
            status = (
                StockistHandoffStatus.PENDING_PHYSICAL_DATA
            )
            line_completed_by = None

        return StockistHandoffLine(
            line_number=line.line_number,
            product_id=line.product_id,
            fiscal_quantity=line.fiscal_quantity,
            quantity_to_receive=line.quantity_to_receive,
            divergence=line.divergence,
            counted_by=line.counted_by,
            batch_code=line.batch_code,
            expiration_date=line.expiration_date,
            manufacturing_date=line.manufacturing_date,
            status=status,
            completed_by=line_completed_by,
        )
