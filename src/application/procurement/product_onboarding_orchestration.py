"""
NF-001E — Explicit Human Product Onboarding Orchestration.

This application boundary exists after unresolved fiscal-product evidence
has been presented to a human operator.

The operator must explicitly confirm the catalog master data before this
service delegates product creation to the existing catalog authority.

This module deliberately does not:
- consume unresolved-product workflows automatically;
- infer product master data;
- reconcile invoices;
- receive goods;
- create batches;
- mutate stock;
- perform putaway.

Fiscal quantity remains evidence only.
"""

from dataclasses import dataclass
from typing import Optional


def _required_text(
    value,
    field_name: str,
) -> str:
    normalized = str(value or "").strip()

    if not normalized:
        raise ValueError(
            f"{field_name} is required"
        )

    return normalized


def _optional_text(value) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class HumanProductOnboardingCommand:
    """
    Explicit human decision combining immutable fiscal evidence with
    operator-confirmed catalog master data.

    Fiscal fields are evidence.

    Only the confirmed_* fields may be delegated to product registration.
    """

    pending_reason: str

    invoice_number: str
    supplier_id: str
    line_number: int

    fiscal_description: str
    fiscal_gtin: str
    fiscal_quantity: object
    fiscal_unit: str

    confirmed_name: str
    confirmed_ean: str
    confirmed_unit_of_measure: str
    confirmed_category_id: Optional[str] = None

    def __post_init__(self):
        object.__setattr__(
            self,
            "pending_reason",
            _required_text(
                self.pending_reason,
                "pending_reason",
            ),
        )

        object.__setattr__(
            self,
            "invoice_number",
            _required_text(
                self.invoice_number,
                "invoice_number",
            ),
        )

        object.__setattr__(
            self,
            "supplier_id",
            _required_text(
                self.supplier_id,
                "supplier_id",
            ),
        )

        object.__setattr__(
            self,
            "fiscal_description",
            _optional_text(
                self.fiscal_description
            ),
        )

        object.__setattr__(
            self,
            "fiscal_gtin",
            _optional_text(
                self.fiscal_gtin
            ),
        )

        object.__setattr__(
            self,
            "fiscal_unit",
            _optional_text(
                self.fiscal_unit
            ),
        )

        object.__setattr__(
            self,
            "confirmed_name",
            _required_text(
                self.confirmed_name,
                "confirmed_name",
            ),
        )

        object.__setattr__(
            self,
            "confirmed_ean",
            _required_text(
                self.confirmed_ean,
                "confirmed_ean",
            ),
        )

        object.__setattr__(
            self,
            "confirmed_unit_of_measure",
            _required_text(
                self.confirmed_unit_of_measure,
                "confirmed_unit_of_measure",
            ),
        )

        if self.confirmed_category_id is not None:
            normalized_category = _optional_text(
                self.confirmed_category_id
            )

            object.__setattr__(
                self,
                "confirmed_category_id",
                normalized_category or None,
            )


class HumanProductOnboardingOrchestrator:
    """
    Minimal explicit human catalog-onboarding boundary.

    The injected repository is the existing product-registration authority.

    No stock or receiving authority is accepted as a dependency.
    """

    def __init__(
        self,
        repository,
    ):
        self.repository = repository

    def execute(
        self,
        command: HumanProductOnboardingCommand,
    ):
        """
        Delegate only operator-confirmed catalog master data.

        Fiscal quantity, invoice evidence and supplier evidence never cross
        into product-registration authority.
        """

        return self.repository.register_new_product(
            name=command.confirmed_name,
            ean=command.confirmed_ean,
            unit_of_measure=(
                command.confirmed_unit_of_measure
            ),
            status="ATIVO",
            category_id=(
                command.confirmed_category_id
            ),
        )
