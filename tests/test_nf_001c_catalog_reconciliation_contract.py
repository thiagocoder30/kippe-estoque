"""
NF-001C — Deterministic Catalog Reconciliation Contract

Purpose:
- reconcile canonical fiscal lines with the existing Kippe catalog;
- use exact GTIN/EAN identity only;
- classify unresolved lines for human/catalog workflow.

Explicitly outside this slice:
- fuzzy description matching;
- automatic product creation;
- persistence of the invoice;
- HTTP;
- OCR/XML parsing;
- receiving;
- stock mutation;
- putaway.
"""

from dataclasses import dataclass

from src.application.procurement.invoice_reconciliation import (
    CatalogReconciliationService,
    ReconciliationStatus,
)
from src.domain.procurement.invoice import (
    SupplierInvoice,
    SupplierInvoiceLine,
)
from src.domain.procurement.order import MonetaryValue


@dataclass
class CatalogProductStub:
    id: str
    ean: str
    name: str = "Produto"


class CatalogRepositoryStub:
    def __init__(self, products=None):
        self.products = {
            product.ean: product
            for product in (products or [])
        }
        self.queries = []

    def get_by_ean(self, ean):
        self.queries.append(ean)
        return self.products.get(ean)


def make_line(
    *,
    gtin="7891234567890",
    description="CAFE TORRADO 500G",
    supplier_product_code="FORN-001",
):
    return SupplierInvoiceLine(
        sku="",
        quantity=2,
        unit_price=MonetaryValue(9.90),
        supplier_product_code=supplier_product_code,
        description=description,
        gtin=gtin,
        commercial_unit="UN",
    )


def make_invoice(*lines):
    return SupplierInvoice(
        invoice_number="NF-001C",
        supplier_id="SUP-001",
        origin_document="OCR",
        lines=list(lines),
    )


def test_exact_gtin_match_assigns_existing_internal_sku():
    product = CatalogProductStub(
        id="SKU000123",
        ean="7891234567890",
    )
    repository = CatalogRepositoryStub([product])

    invoice = make_invoice(make_line())

    result = CatalogReconciliationService(
        repository
    ).reconcile(invoice)

    assert len(result.lines) == 1

    reconciled = result.lines[0]

    assert reconciled.status == ReconciliationStatus.MATCHED
    assert reconciled.product_id == "SKU000123"
    assert reconciled.invoice_line.sku == "SKU000123"
    assert repository.queries == ["7891234567890"]


def test_unknown_gtin_is_classified_for_registration_without_creating_product():
    repository = CatalogRepositoryStub()

    invoice = make_invoice(
        make_line(gtin="7899999999999")
    )

    result = CatalogReconciliationService(
        repository
    ).reconcile(invoice)

    reconciled = result.lines[0]

    assert (
        reconciled.status
        == ReconciliationStatus.NEEDS_REGISTRATION
    )
    assert reconciled.product_id == ""
    assert reconciled.invoice_line.sku == ""

    # Read-only reconciliation: repository exposes no save requirement.
    assert not hasattr(repository, "save_calls")


def test_missing_gtin_does_not_attempt_description_guessing():
    repository = CatalogRepositoryStub(
        [
            CatalogProductStub(
                id="SKU000777",
                ean="7890000000777",
                name="CAFE TORRADO 500G",
            )
        ]
    )

    invoice = make_invoice(
        make_line(
            gtin="",
            description="CAFE TORRADO 500G",
        )
    )

    result = CatalogReconciliationService(
        repository
    ).reconcile(invoice)

    reconciled = result.lines[0]

    assert (
        reconciled.status
        == ReconciliationStatus.NEEDS_REGISTRATION
    )
    assert reconciled.product_id == ""
    assert reconciled.invoice_line.sku == ""

    # No fuzzy/name lookup and no meaningless empty-EAN query.
    assert repository.queries == []


def test_multiple_lines_are_reconciled_independently():
    repository = CatalogRepositoryStub(
        [
            CatalogProductStub(
                id="SKU-A",
                ean="7890000000001",
            )
        ]
    )

    invoice = make_invoice(
        make_line(
            gtin="7890000000001",
            supplier_product_code="A",
        ),
        make_line(
            gtin="7890000000002",
            supplier_product_code="B",
        ),
    )

    result = CatalogReconciliationService(
        repository
    ).reconcile(invoice)

    assert len(result.lines) == 2

    assert (
        result.lines[0].status
        == ReconciliationStatus.MATCHED
    )
    assert result.lines[0].product_id == "SKU-A"
    assert result.lines[0].invoice_line.sku == "SKU-A"

    assert (
        result.lines[1].status
        == ReconciliationStatus.NEEDS_REGISTRATION
    )
    assert result.lines[1].product_id == ""
    assert result.lines[1].invoice_line.sku == ""


def test_reconciliation_reports_summary_counts():
    repository = CatalogRepositoryStub(
        [
            CatalogProductStub(
                id="SKU-A",
                ean="7890000000001",
            )
        ]
    )

    invoice = make_invoice(
        make_line(gtin="7890000000001"),
        make_line(gtin="7890000000002"),
        make_line(gtin=""),
    )

    result = CatalogReconciliationService(
        repository
    ).reconcile(invoice)

    assert result.total_lines == 3
    assert result.matched_lines == 1
    assert result.needs_registration_lines == 2
    assert result.is_fully_reconciled is False


def test_fully_known_invoice_is_reported_as_fully_reconciled():
    repository = CatalogRepositoryStub(
        [
            CatalogProductStub(
                id="SKU-A",
                ean="7890000000001",
            ),
            CatalogProductStub(
                id="SKU-B",
                ean="7890000000002",
            ),
        ]
    )

    invoice = make_invoice(
        make_line(gtin="7890000000001"),
        make_line(gtin="7890000000002"),
    )

    result = CatalogReconciliationService(
        repository
    ).reconcile(invoice)

    assert result.total_lines == 2
    assert result.matched_lines == 2
    assert result.needs_registration_lines == 0
    assert result.is_fully_reconciled is True


def test_reconciliation_service_has_no_stock_mutation_surface():
    service = CatalogReconciliationService(
        CatalogRepositoryStub()
    )

    assert not hasattr(service, "receive")
    assert not hasattr(service, "receive_stock")
    assert not hasattr(service, "putaway")
    assert not hasattr(service, "add_stock")
