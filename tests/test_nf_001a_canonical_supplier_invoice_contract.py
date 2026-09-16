"""
NF-001A — Canonical Supplier Invoice Contract

Este contrato estabelece somente a representação canônica da NF de entrada.

Não testa:
- OCR;
- leitura de DANFE;
- XML;
- HTTP;
- persistência;
- mutação de estoque;
- recebimento;
- putaway.

A NF estruturada é expectativa documental.
Ela não possui autoridade para alterar estoque.
"""

from src.domain.procurement.invoice import (
    SupplierInvoice,
    SupplierInvoiceLine,
)
from src.domain.procurement.order import MonetaryValue


def test_supplier_invoice_preserves_canonical_nf_identity():
    invoice = SupplierInvoice(
        invoice_number="000123456",
        supplier_id="SUP-001",
        access_key="1" * 44,
        series="1",
        origin_document="OCR",
    )

    assert invoice.invoice_number == "000123456"
    assert invoice.supplier_id == "SUP-001"
    assert invoice.access_key == "1" * 44
    assert invoice.series == "1"
    assert invoice.origin_document == "OCR"


def test_supplier_invoice_line_preserves_fiscal_product_identity():
    line = SupplierInvoiceLine(
        sku="SKU-001",
        quantity=12,
        unit_price=MonetaryValue(9.90),
        supplier_product_code="FORN-7788",
        description="CAFE TORRADO 500G",
        gtin="7891234567890",
        commercial_unit="UN",
    )

    assert line.sku == "SKU-001"
    assert line.supplier_product_code == "FORN-7788"
    assert line.description == "CAFE TORRADO 500G"
    assert line.gtin == "7891234567890"
    assert line.commercial_unit == "UN"
    assert line.quantity == 12


def test_canonical_invoice_accepts_unmatched_product_without_fabricating_sku():
    line = SupplierInvoiceLine(
        sku="",
        quantity=6,
        unit_price=MonetaryValue(4.50),
        supplier_product_code="ABC-991",
        description="PRODUTO NOVO DO FORNECEDOR",
        gtin="7899999999999",
        commercial_unit="UN",
    )

    assert line.sku == ""
    assert line.supplier_product_code == "ABC-991"
    assert line.description == "PRODUTO NOVO DO FORNECEDOR"


def test_origin_document_supports_current_and_future_ingestion_sources():
    for origin in (
        "MANUAL",
        "OCR",
        "XML",
    ):
        invoice = SupplierInvoice(
            invoice_number=f"NF-{origin}",
            supplier_id="SUP-001",
            origin_document=origin,
        )

        assert invoice.origin_document == origin


def test_supplier_invoice_remains_documentary_and_does_not_mutate_stock():
    invoice = SupplierInvoice(
        invoice_number="NF-IMMUTABLE-STOCK",
        supplier_id="SUP-001",
        access_key="2" * 44,
        origin_document="OCR",
    )

    invoice.lines.append(
        SupplierInvoiceLine(
            sku="SKU-001",
            quantity=10,
            unit_price=MonetaryValue(5.00),
            description="ITEM DOCUMENTAL",
            commercial_unit="UN",
        )
    )

    # O contrato canônico da NF não recebe repository,
    # ReceivingUseCase ou qualquer porta de mutação quantitativa.
    assert not hasattr(invoice, "receive")
    assert not hasattr(invoice, "receive_stock")
    assert not hasattr(invoice, "save_product")
    assert invoice.lines[0].quantity == 10


def test_existing_three_way_match_surface_remains_available():
    """
    NF-001A estende SupplierInvoice em vez de criar InvoiceDraft
    paralelo. O contrato histórico necessário ao ThreeWayMatch
    precisa continuar existindo.
    """
    invoice = SupplierInvoice(
        invoice_number="NF-COMPAT",
        supplier_id="SUP-COMPAT",
    )

    invoice.lines.append(
        SupplierInvoiceLine(
            sku="SKU-COMPAT",
            quantity=2,
            unit_price=MonetaryValue(3.00),
        )
    )

    assert invoice.invoice_number == "NF-COMPAT"
    assert invoice.supplier_id == "SUP-COMPAT"
    assert invoice.lines[0].sku == "SKU-COMPAT"
    assert invoice.lines[0].quantity == 2
