"""
NF-001D — Unresolved Product Workflow

Pure application boundary that transforms unresolved catalog-reconciliation
evidence into explicit human catalog actions.

Responsibilities
----------------
It may:
- identify reconciliation lines that require catalog registration;
- preserve the fiscal evidence required by a human operator;
- distinguish missing GTIN from an unknown GTIN;
- expose a deterministic list of pending catalog actions.

It must not:
- create products;
- call product onboarding;
- persist workflow tasks;
- mutate invoices;
- mutate the product catalog;
- receive goods;
- mutate stock;
- perform putaway;
- expose HTTP.

Product creation remains behind the existing explicit onboarding authority.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List

from src.application.procurement.invoice_reconciliation import (
    CatalogReconciliationResult,
    ReconciliationStatus,
)


class UnresolvedProductReason(str, Enum):
    """
    Deterministic reason why a fiscal line requires human catalog action.
    """

    MISSING_GTIN = "MISSING_GTIN"
    UNKNOWN_GTIN = "UNKNOWN_GTIN"


@dataclass(frozen=True)
class UnresolvedProductAction:
    """
    Read-only fiscal evidence for one unresolved product.

    This object deliberately contains no Product aggregate and exposes no
    creation or persistence authority.
    """

    invoice_number: str
    supplier_id: str
    supplier_product_code: str
    description: str
    gtin: str
    commercial_unit: str
    quantity: object
    reason: UnresolvedProductReason


@dataclass(frozen=True)
class UnresolvedProductWorkflowResult:
    """
    Deterministic summary of unresolved catalog actions for one invoice.
    """

    pending: List[UnresolvedProductAction]

    @property
    def total_pending(self) -> int:
        return len(self.pending)

    @property
    def is_clear(self) -> bool:
        return self.total_pending == 0


class UnresolvedProductWorkflowService:
    """
    Builds a human-action queue from catalog-reconciliation evidence.

    The service is intentionally pure. It receives the result of NF-001C
    and returns workflow evidence only.
    """

    @staticmethod
    def _text(value) -> str:
        return str(value or "").strip()

    @classmethod
    def _reason_for_gtin(
        cls,
        gtin,
    ) -> UnresolvedProductReason:
        if not cls._text(gtin):
            return UnresolvedProductReason.MISSING_GTIN

        return UnresolvedProductReason.UNKNOWN_GTIN

    def build(
        self,
        reconciliation: CatalogReconciliationResult,
    ) -> UnresolvedProductWorkflowResult:
        invoice = reconciliation.invoice

        pending = []

        for reconciled_line in reconciliation.lines:
            if (
                reconciled_line.status
                != ReconciliationStatus.NEEDS_REGISTRATION
            ):
                continue

            fiscal_line = reconciled_line.invoice_line

            gtin = self._text(
                getattr(
                    fiscal_line,
                    "gtin",
                    "",
                )
            )

            pending.append(
                UnresolvedProductAction(
                    invoice_number=self._text(
                        getattr(
                            invoice,
                            "invoice_number",
                            "",
                        )
                    ),
                    supplier_id=self._text(
                        getattr(
                            invoice,
                            "supplier_id",
                            "",
                        )
                    ),
                    supplier_product_code=self._text(
                        getattr(
                            fiscal_line,
                            "supplier_product_code",
                            "",
                        )
                    ),
                    description=self._text(
                        getattr(
                            fiscal_line,
                            "description",
                            "",
                        )
                    ),
                    gtin=gtin,
                    commercial_unit=self._text(
                        getattr(
                            fiscal_line,
                            "commercial_unit",
                            "",
                        )
                    ),
                    quantity=getattr(
                        fiscal_line,
                        "quantity",
                        0,
                    ),
                    reason=self._reason_for_gtin(
                        gtin
                    ),
                )
            )

        return UnresolvedProductWorkflowResult(
            pending=pending
        )
