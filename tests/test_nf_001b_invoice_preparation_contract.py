"""
NF-001B — Ingestion-Neutral Invoice Preparation Contract

This contract defines the boundary between extracted fiscal data and the
canonical SupplierInvoice domain model.

It intentionally does NOT implement:
- OCR;
- DANFE parsing;
- XML parsing;
- HTTP;
- persistence;
- stock mutation;
- receiving;
- putaway.

Any ingestion mechanism must be able to produce the same neutral input.
"""

import pytest

from src.application.procurement.invoice_preparation import (
    ExtractedInvoiceData,
    ExtractedInvoiceLineData,
    InvoicePreparationService,
)


def test_prepares_canonical_invoice_from_ingestion_neutral_data():
    extracted = ExtractedInvoiceData(
        invoice_number="000123456",
        supplier_id="SUP-001",
        access_key="1" * 44,
        series="1",
        origin_document="OCR",
        lines=[
            ExtractedInvoiceLineData(
                supplier_product_code="FORN-7788",
                description="CAFE TORRADO 500G",
                gtin="7891234567890",
                commercial_unit="UN",
                quantity=12,
                unit_price=9.90,
            )
        ],
    )

    invoice = InvoicePreparationService().prepare(extracted)

    assert invoice.invoice_number == "000123456"
    assert invoice.supplier_id == "SUP-001"
    assert invoice.access_key == "1" * 44
    assert invoice.series == "1"
    assert invoice.origin_document == "OCR"

    assert len(invoice.lines) == 1

    line = invoice.lines[0]

    assert line.sku == ""
    assert line.supplier_product_code == "FORN-7788"
    assert line.description == "CAFE TORRADO 500G"
    assert line.gtin == "7891234567890"
    assert line.commercial_unit == "UN"
    assert line.quantity == 12
    assert line.unit_price.amount == pytest.approx(9.90)


def test_preparation_does_not_require_internal_sku():
    extracted = ExtractedInvoiceData(
        invoice_number="NF-NEW-PRODUCT",
        supplier_id="SUP-002",
        origin_document="MANUAL",
        lines=[
            ExtractedInvoiceLineData(
                supplier_product_code="NEW-001",
                description="PRODUTO AINDA NAO CADASTRADO",
                gtin="7899999999999",
                commercial_unit="CX",
                quantity=4,
                unit_price=15.75,
            )
        ],
    )

    invoice = InvoicePreparationService().prepare(extracted)

    assert invoice.lines[0].sku == ""
    assert invoice.lines[0].supplier_product_code == "NEW-001"


@pytest.mark.parametrize("origin", ["MANUAL", "OCR", "XML"])
def test_preparation_is_ingestion_source_neutral(origin):
    extracted = ExtractedInvoiceData(
        invoice_number=f"NF-{origin}",
        supplier_id="SUP-001",
        origin_document=origin,
        lines=[
            ExtractedInvoiceLineData(
                supplier_product_code="P-1",
                description="ITEM",
                gtin="",
                commercial_unit="UN",
                quantity=1,
                unit_price=1.50,
            )
        ],
    )

    invoice = InvoicePreparationService().prepare(extracted)

    assert invoice.origin_document == origin
    assert invoice.invoice_number == f"NF-{origin}"


def test_preparation_preserves_multiple_fiscal_lines():
    extracted = ExtractedInvoiceData(
        invoice_number="NF-MULTI",
        supplier_id="SUP-001",
        origin_document="XML",
        lines=[
            ExtractedInvoiceLineData(
                supplier_product_code="A",
                description="ITEM A",
                gtin="7890000000001",
                commercial_unit="UN",
                quantity=2,
                unit_price=3.25,
            ),
            ExtractedInvoiceLineData(
                supplier_product_code="B",
                description="ITEM B",
                gtin="7890000000002",
                commercial_unit="CX",
                quantity=5,
                unit_price=7.10,
            ),
        ],
    )

    invoice = InvoicePreparationService().prepare(extracted)

    assert len(invoice.lines) == 2
    assert invoice.lines[0].supplier_product_code == "A"
    assert invoice.lines[1].supplier_product_code == "B"
    assert invoice.lines[0].quantity == 2
    assert invoice.lines[1].quantity == 5


def test_preparation_does_not_expose_stock_mutation_ports():
    service = InvoicePreparationService()

    assert not hasattr(service, "receive")
    assert not hasattr(service, "receive_stock")
    assert not hasattr(service, "save_product")
    assert not hasattr(service, "putaway")


def test_invalid_fiscal_quantity_is_rejected_by_canonical_domain():
    extracted = ExtractedInvoiceData(
        invoice_number="NF-INVALID",
        supplier_id="SUP-001",
        origin_document="OCR",
        lines=[
            ExtractedInvoiceLineData(
                supplier_product_code="BAD",
                description="ITEM INVALIDO",
                gtin="",
                commercial_unit="UN",
                quantity=0,
                unit_price=1.00,
            )
        ],
    )

    with pytest.raises(
        ValueError,
        match="quantidade faturada",
    ):
        InvoicePreparationService().prepare(extracted)
