"""
NF-001D — Unresolved Product Workflow Contract

Transforms catalog-reconciliation evidence into an explicit human workflow.

This slice does NOT:
- create products;
- call product onboarding;
- persist tasks;
- expose HTTP;
- mutate stock;
- perform receiving;
- perform putaway.

It only describes which fiscal lines require catalog action.
"""

from src.application.procurement.invoice_reconciliation import (
    CatalogReconciliationResult,
    ReconciledInvoiceLine,
    ReconciliationStatus,
)
from src.application.procurement.unresolved_product_workflow import (
    UnresolvedProductWorkflowService,
    UnresolvedProductReason,
)
from src.domain.procurement.invoice import (
    SupplierInvoice,
    SupplierInvoiceLine,
)
from src.domain.procurement.order import MonetaryValue


def line(
    *,
    gtin="",
    code="FORN-001",
    description="PRODUTO TESTE",
    unit="UN",
):
    return SupplierInvoiceLine(
        sku="",
        quantity=2,
        unit_price=MonetaryValue(5.00),
        supplier_product_code=code,
        description=description,
        gtin=gtin,
        commercial_unit=unit,
    )


def invoice_with(*lines):
    return SupplierInvoice(
        invoice_number="NF-001D",
        supplier_id="SUP-001",
        origin_document="OCR",
        lines=list(lines),
    )


def test_unknown_gtin_generates_catalog_action():
    fiscal_line = line(
        gtin="7899999999999",
        code="NEW-001",
        description="PRODUTO NOVO",
    )

    invoice = invoice_with(fiscal_line)

    reconciliation = CatalogReconciliationResult(
        invoice=invoice,
        lines=[
            ReconciledInvoiceLine(
                invoice_line=fiscal_line,
                status=ReconciliationStatus.NEEDS_REGISTRATION,
                product_id="",
            )
        ],
    )

    result = UnresolvedProductWorkflowService().build(
        reconciliation
    )

    assert result.total_pending == 1

    pending = result.pending[0]

    assert pending.invoice_number == "NF-001D"
    assert pending.supplier_id == "SUP-001"
    assert pending.supplier_product_code == "NEW-001"
    assert pending.description == "PRODUTO NOVO"
    assert pending.gtin == "7899999999999"
    assert pending.commercial_unit == "UN"
    assert pending.quantity == 2
    assert pending.reason == UnresolvedProductReason.UNKNOWN_GTIN


def test_missing_gtin_is_distinguished_from_unknown_gtin():
    fiscal_line = line(
        gtin="",
        code="NO-EAN",
    )

    reconciliation = CatalogReconciliationResult(
        invoice=invoice_with(fiscal_line),
        lines=[
            ReconciledInvoiceLine(
                invoice_line=fiscal_line,
                status=ReconciliationStatus.NEEDS_REGISTRATION,
                product_id="",
            )
        ],
    )

    result = UnresolvedProductWorkflowService().build(
        reconciliation
    )

    assert result.total_pending == 1
    assert (
        result.pending[0].reason
        == UnresolvedProductReason.MISSING_GTIN
    )


def test_matched_products_do_not_generate_catalog_actions():
    fiscal_line = line(
        gtin="7891234567890"
    )
    fiscal_line.sku = "SKU-001"

    reconciliation = CatalogReconciliationResult(
        invoice=invoice_with(fiscal_line),
        lines=[
            ReconciledInvoiceLine(
                invoice_line=fiscal_line,
                status=ReconciliationStatus.MATCHED,
                product_id="SKU-001",
            )
        ],
    )

    result = UnresolvedProductWorkflowService().build(
        reconciliation
    )

    assert result.total_pending == 0
    assert result.pending == []


def test_multiple_unresolved_lines_remain_independent():
    first = line(
        gtin="7890000000001",
        code="A",
    )
    second = line(
        gtin="",
        code="B",
    )

    reconciliation = CatalogReconciliationResult(
        invoice=invoice_with(first, second),
        lines=[
            ReconciledInvoiceLine(
                invoice_line=first,
                status=ReconciliationStatus.NEEDS_REGISTRATION,
                product_id="",
            ),
            ReconciledInvoiceLine(
                invoice_line=second,
                status=ReconciliationStatus.NEEDS_REGISTRATION,
                product_id="",
            ),
        ],
    )

    result = UnresolvedProductWorkflowService().build(
        reconciliation
    )

    assert result.total_pending == 2
    assert result.pending[0].supplier_product_code == "A"
    assert result.pending[1].supplier_product_code == "B"

    assert (
        result.pending[0].reason
        == UnresolvedProductReason.UNKNOWN_GTIN
    )
    assert (
        result.pending[1].reason
        == UnresolvedProductReason.MISSING_GTIN
    )


def test_pending_action_preserves_fiscal_evidence_without_product_creation():
    fiscal_line = line(
        gtin="7895555555555",
        code="SUP-555",
        description="ITEM PARA CADASTRO",
        unit="CX",
    )

    reconciliation = CatalogReconciliationResult(
        invoice=invoice_with(fiscal_line),
        lines=[
            ReconciledInvoiceLine(
                invoice_line=fiscal_line,
                status=ReconciliationStatus.NEEDS_REGISTRATION,
                product_id="",
            )
        ],
    )

    result = UnresolvedProductWorkflowService().build(
        reconciliation
    )

    pending = result.pending[0]

    assert pending.gtin == "7895555555555"
    assert pending.supplier_product_code == "SUP-555"
    assert pending.description == "ITEM PARA CADASTRO"
    assert pending.commercial_unit == "CX"

    assert not hasattr(pending, "product")
    assert not hasattr(pending, "created_product")


def test_workflow_service_has_no_catalog_or_stock_write_surface():
    service = UnresolvedProductWorkflowService()

    assert not hasattr(service, "register_product")
    assert not hasattr(service, "save")
    assert not hasattr(service, "receive")
    assert not hasattr(service, "receive_stock")
    assert not hasattr(service, "putaway")
    assert not hasattr(service, "add_stock")
