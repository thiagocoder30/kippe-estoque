"""
Ingestion-neutral preparation of supplier invoices.

This module is the application boundary between extraction mechanisms
(manual entry, OCR, XML, or future sources) and the canonical procurement
domain model.

It does not perform extraction, persistence, receiving, putaway, or stock
mutation.
"""

from dataclasses import dataclass, field
from typing import List

from src.domain.procurement.invoice import (
    SupplierInvoice,
    SupplierInvoiceLine,
)
from src.domain.procurement.order import MonetaryValue


@dataclass
class ExtractedInvoiceLineData:
    """
    Neutral fiscal line produced by an ingestion mechanism.

    No internal Kippe SKU is required at this boundary because catalog
    reconciliation occurs after documentary preparation.
    """

    supplier_product_code: str
    description: str
    gtin: str
    commercial_unit: str
    quantity: int
    unit_price: float


@dataclass
class ExtractedInvoiceData:
    """
    Neutral structured representation of an extracted supplier invoice.
    """

    invoice_number: str
    supplier_id: str
    lines: List[ExtractedInvoiceLineData] = field(default_factory=list)
    access_key: str = ""
    series: str = ""
    origin_document: str = "MANUAL"


class InvoicePreparationService:
    """
    Converts ingestion-neutral fiscal data into SupplierInvoice.

    This service deliberately has no repository or stock dependency.
    """

    def prepare(
        self,
        extracted: ExtractedInvoiceData,
    ) -> SupplierInvoice:
        lines = [
            SupplierInvoiceLine(
                sku="",
                quantity=line.quantity,
                unit_price=MonetaryValue(line.unit_price),
                supplier_product_code=line.supplier_product_code,
                description=line.description,
                gtin=line.gtin,
                commercial_unit=line.commercial_unit,
            )
            for line in extracted.lines
        ]

        return SupplierInvoice(
            invoice_number=extracted.invoice_number,
            supplier_id=extracted.supplier_id,
            lines=lines,
            access_key=extracted.access_key,
            series=extracted.series,
            origin_document=extracted.origin_document,
        )
