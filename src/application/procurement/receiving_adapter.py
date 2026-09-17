"""
NF-001J.5 — Pure Receiving Adapter.

This module is the pure boundary between the certified Stockist Handoff
contract and the existing ReceivingUseCase.

Its only responsibility is to build an immutable receiving command from
a line explicitly marked READY_FOR_RECEIVING.

It deliberately does NOT:
- instantiate ReceivingUseCase;
- execute receiving;
- access repositories;
- access SQLite;
- persist anything;
- mutate product stock;
- create batches;
- execute putaway;
- provide retry/idempotency execution semantics.

Actual receiving execution is deferred to a later certified boundary.
"""

from dataclasses import dataclass
from typing import Optional

from src.application.procurement.stockist_handoff import (
    StockistHandoffLine,
    StockistHandoffResult,
    StockistHandoffStatus,
)


@dataclass(frozen=True)
class ReceivingCommand:
    """
    Immutable command compatible with ReceivingUseCase.execute().
    """

    identifier: str
    quantity: int
    batch_code: str
    expiration_date: str
    supplier: str
    manufacturing_date: str
    invoice_id: str
    origin_document: str
    operator_id: str


class ReceivingAdapter:
    """
    Pure mapper from certified stockist handoff evidence to ReceivingCommand.
    """

    ORIGIN_DOCUMENT = "SUPPLIER_INVOICE"

    @classmethod
    def build_command(
        cls,
        handoff: StockistHandoffResult,
        *,
        line_number: int,
    ) -> ReceivingCommand:
        if not isinstance(
            handoff,
            StockistHandoffResult,
        ):
            raise TypeError(
                "Receiving adapter requires "
                "StockistHandoffResult."
            )

        line = handoff.get_line(line_number)

        return cls.build_line_command(
            handoff,
            line,
        )

    @classmethod
    def build_line_command(
        cls,
        handoff: StockistHandoffResult,
        line: StockistHandoffLine,
    ) -> ReceivingCommand:
        if not isinstance(
            handoff,
            StockistHandoffResult,
        ):
            raise TypeError(
                "Receiving adapter requires "
                "StockistHandoffResult."
            )

        if not isinstance(
            line,
            StockistHandoffLine,
        ):
            raise TypeError(
                "Receiving adapter requires "
                "StockistHandoffLine."
            )

        if (
            line.status
            != StockistHandoffStatus.READY_FOR_RECEIVING
        ):
            raise ValueError(
                "Somente linhas READY_FOR_RECEIVING "
                "podem gerar comando de recebimento."
            )

        identifier = cls._required_text(
            line.product_id,
            "product_id",
        )

        quantity = cls._positive_quantity(
            line.quantity_to_receive,
        )

        batch_code = cls._required_text(
            line.batch_code,
            "batch_code",
        )

        expiration_date = cls._required_text(
            line.expiration_date,
            "expiration_date",
        )

        supplier = cls._required_text(
            handoff.supplier_id,
            "supplier_id",
        )

        invoice_id = cls._required_text(
            handoff.invoice_number,
            "invoice_number",
        )

        operator_id = cls._required_text(
            line.completed_by,
            "completed_by",
        )

        manufacturing_date = cls._optional_text(
            line.manufacturing_date,
        )

        return ReceivingCommand(
            identifier=identifier,
            quantity=quantity,
            batch_code=batch_code,
            expiration_date=expiration_date,
            supplier=supplier,
            manufacturing_date=manufacturing_date,
            invoice_id=invoice_id,
            origin_document=cls.ORIGIN_DOCUMENT,
            operator_id=operator_id,
        )

    @staticmethod
    def _required_text(
        value: Optional[str],
        field_name: str,
    ) -> str:
        normalized = str(
            value or ""
        ).strip()

        if not normalized:
            raise ValueError(
                f"{field_name} é obrigatório para "
                "gerar comando de recebimento."
            )

        return normalized

    @staticmethod
    def _optional_text(
        value: Optional[str],
    ) -> str:
        if value is None:
            return ""

        return str(value).strip()

    @staticmethod
    def _positive_quantity(
        value: int,
    ) -> int:
        if isinstance(value, bool):
            raise ValueError(
                "quantity_to_receive deve ser "
                "um inteiro positivo."
            )

        try:
            quantity = int(value)
        except (TypeError, ValueError):
            raise ValueError(
                "quantity_to_receive deve ser "
                "um inteiro positivo."
            ) from None

        if quantity != value or quantity <= 0:
            raise ValueError(
                "quantity_to_receive deve ser "
                "maior que zero."
            )

        return quantity
