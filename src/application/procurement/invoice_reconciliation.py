"""
Application service for deterministic reconciliation between canonical
supplier-invoice lines and the existing Kippe product catalog.

NF-001C boundary
----------------
This module is deliberately read-only with respect to the catalog and
inventory.

It may:
- query an existing product by exact GTIN/EAN;
- associate a canonical fiscal line with the internal product id;
- classify unresolved lines for the explicit catalog workflow.

It must not:
- perform fuzzy/name matching;
- create products;
- persist invoices;
- receive goods;
- mutate stock;
- perform putaway.

The catalog remains the authority for product identity.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from src.domain.procurement.invoice import (
    SupplierInvoice,
    SupplierInvoiceLine,
)


class ReconciliationStatus(str, Enum):
    """
    Outcome of deterministic catalog reconciliation for one fiscal line.
    """

    MATCHED = "MATCHED"
    NEEDS_REGISTRATION = "NEEDS_REGISTRATION"


@dataclass(frozen=True)
class ReconciledInvoiceLine:
    """
    Reconciliation evidence for one canonical supplier-invoice line.

    product_id remains empty when no deterministic catalog identity exists.
    """

    invoice_line: SupplierInvoiceLine
    status: ReconciliationStatus
    product_id: str = ""


@dataclass(frozen=True)
class CatalogReconciliationResult:
    """
    Read-only summary of reconciliation for one SupplierInvoice.
    """

    invoice: SupplierInvoice
    lines: List[ReconciledInvoiceLine]

    @property
    def total_lines(self) -> int:
        return len(self.lines)

    @property
    def matched_lines(self) -> int:
        return sum(
            1
            for line in self.lines
            if line.status == ReconciliationStatus.MATCHED
        )

    @property
    def needs_registration_lines(self) -> int:
        return sum(
            1
            for line in self.lines
            if (
                line.status
                == ReconciliationStatus.NEEDS_REGISTRATION
            )
        )

    @property
    def is_fully_reconciled(self) -> bool:
        return (
            self.total_lines > 0
            and self.matched_lines == self.total_lines
        )


class CatalogReconciliationService:
    """
    Deterministic application service for fiscal-line catalog identity.

    The injected catalog repository needs only the read capability
    ``get_by_ean(ean)``.

    No write capability is required or invoked.
    """

    def __init__(self, catalog_repository):
        self.catalog_repository = catalog_repository

    @staticmethod
    def _normalize_gtin(value: Optional[str]) -> str:
        return str(value or "").strip()

    def _reconcile_line(
        self,
        invoice_line: SupplierInvoiceLine,
    ) -> ReconciledInvoiceLine:
        gtin = self._normalize_gtin(
            invoice_line.gtin
        )

        if not gtin:
            return ReconciledInvoiceLine(
                invoice_line=invoice_line,
                status=(
                    ReconciliationStatus
                    .NEEDS_REGISTRATION
                ),
                product_id="",
            )

        product = (
            self.catalog_repository
            .get_by_ean(gtin)
        )

        if product is None:
            return ReconciledInvoiceLine(
                invoice_line=invoice_line,
                status=(
                    ReconciliationStatus
                    .NEEDS_REGISTRATION
                ),
                product_id="",
            )

        product_id = str(
            getattr(product, "id", "") or ""
        ).strip()

        if not product_id:
            return ReconciledInvoiceLine(
                invoice_line=invoice_line,
                status=(
                    ReconciliationStatus
                    .NEEDS_REGISTRATION
                ),
                product_id="",
            )

        invoice_line.sku = product_id

        return ReconciledInvoiceLine(
            invoice_line=invoice_line,
            status=ReconciliationStatus.MATCHED,
            product_id=product_id,
        )

    def reconcile(
        self,
        invoice: SupplierInvoice,
    ) -> CatalogReconciliationResult:
        reconciled_lines = [
            self._reconcile_line(line)
            for line in invoice.lines
        ]

        return CatalogReconciliationResult(
            invoice=invoice,
            lines=reconciled_lines,
        )
