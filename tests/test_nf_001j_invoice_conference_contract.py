"""
NF-001J — Physical conference contract.

The conference boundary must preserve the existing NF architecture:

SupplierInvoice
 -> CatalogReconciliationResult
 -> explicit human physical count
 -> explicit ConferenceClosedResult

It must not create products, receive goods, create batches or mutate stock.
"""

import inspect

import pytest

from src.application.procurement.invoice_conference import (
    ConferenceLineStatus,
    ConferenceStatus,
    InvoiceConferenceService,
)
from src.application.procurement.invoice_reconciliation import (
    CatalogReconciliationResult,
    ReconciledInvoiceLine,
    ReconciliationStatus,
)
from src.domain.procurement.invoice import (
    SupplierInvoice,
    SupplierInvoiceLine,
)
from src.domain.procurement.order import MonetaryValue


def fiscal_line(
    *,
    sku="SKU-001",
    quantity=10,
    gtin="7890000000001",
    description="Produto Fiscal",
):
    return SupplierInvoiceLine(
        sku=sku,
        quantity=quantity,
        unit_price=MonetaryValue(5.0),
        supplier_product_code="FORN-001",
        description=description,
        gtin=gtin,
        commercial_unit="UN",
    )


def reconciliation(
    *lines,
):
    invoice = SupplierInvoice(
        invoice_number="NF-001J-TEST",
        supplier_id="SUP-001",
        access_key="CHAVE-001J",
        series="1",
        origin_document="XML",
        lines=[
            item.invoice_line
            for item in lines
        ],
    )

    return CatalogReconciliationResult(
        invoice=invoice,
        lines=list(lines),
    )


def matched_line(
    *,
    sku="SKU-001",
    quantity=10,
):
    line = fiscal_line(
        sku=sku,
        quantity=quantity,
    )

    return ReconciledInvoiceLine(
        invoice_line=line,
        status=ReconciliationStatus.MATCHED,
        product_id=sku,
    )


def unresolved_line(
    *,
    quantity=10,
):
    line = fiscal_line(
        sku="",
        quantity=quantity,
        gtin="7899999999999",
    )

    return ReconciledInvoiceLine(
        invoice_line=line,
        status=ReconciliationStatus.NEEDS_REGISTRATION,
        product_id="",
    )


def test_nf001j_references_existing_invoice_and_reconciliation_evidence():
    result = reconciliation(
        matched_line(),
    )

    session = InvoiceConferenceService.open(
        result,
        "CONF-001",
    )

    assert session.reconciliation is result
    assert session.invoice is result.invoice
    assert session.lines[0].reconciled_line is result.lines[0]
    assert session.lines[0].fiscal_line is result.invoice.lines[0]

    assert session.invoice_number == "NF-001J-TEST"
    assert session.supplier_id == "SUP-001"


def test_nf001j_open_session_does_not_mutate_fiscal_or_catalog_evidence():
    matched = matched_line(
        quantity=12,
    )

    result = reconciliation(matched)

    before_sku = matched.invoice_line.sku
    before_quantity = matched.invoice_line.quantity
    before_product_id = matched.product_id

    session = InvoiceConferenceService.open(
        result,
        "CONF-001",
    )

    assert session.status == ConferenceStatus.OPEN
    assert matched.invoice_line.sku == before_sku
    assert matched.invoice_line.quantity == before_quantity
    assert matched.product_id == before_product_id


def test_nf001j_matched_line_starts_pending_physical_count():
    session = InvoiceConferenceService.open(
        reconciliation(
            matched_line(),
        ),
        "CONF-001",
    )

    line = session.lines[0]

    assert line.status == ConferenceLineStatus.PENDING_COUNT
    assert line.can_count is True
    assert line.counted_quantity is None
    assert line.divergence is None


def test_nf001j_unresolved_catalog_line_is_explicitly_blocked():
    session = InvoiceConferenceService.open(
        reconciliation(
            unresolved_line(),
        ),
        "CONF-001",
    )

    line = session.lines[0]

    assert (
        line.status
        == ConferenceLineStatus.BLOCKED_REGISTRATION
    )
    assert line.can_count is False
    assert session.blocked_lines == 1
    assert session.can_close is False

    with pytest.raises(
        ValueError,
        match="requer cadastro",
    ):
        session.register_count(
            1,
            10,
            "CONF-001",
        )


def test_nf001j_registers_exact_human_count_and_deterministic_divergence():
    session = InvoiceConferenceService.open(
        reconciliation(
            matched_line(
                quantity=12,
            ),
        ),
        "CONF-001",
    )

    line = session.register_count(
        line_number=1,
        quantity=10,
        operator_id="CONF-002",
    )

    assert line.counted_quantity == 10
    assert line.counted_by == "CONF-002"
    assert line.fiscal_quantity == 12
    assert line.divergence == -2
    assert line.is_divergent is True
    assert line.status == ConferenceLineStatus.COUNTED


def test_nf001j_zero_physical_quantity_is_valid_and_divergent():
    session = InvoiceConferenceService.open(
        reconciliation(
            matched_line(
                quantity=7,
            ),
        ),
        "CONF-001",
    )

    line = session.register_count(
        1,
        0,
        "CONF-002",
    )

    assert line.counted_quantity == 0
    assert line.divergence == -7


@pytest.mark.parametrize(
    "quantity",
    [
        -1,
        -100,
        "invalid",
        None,
        True,
        1.5,
    ],
)
def test_nf001j_rejects_invalid_physical_counts(quantity):
    session = InvoiceConferenceService.open(
        reconciliation(
            matched_line(),
        ),
        "CONF-001",
    )

    with pytest.raises(ValueError):
        session.register_count(
            1,
            quantity,
            "CONF-002",
        )


def test_nf001j_requires_explicit_operator_for_count():
    session = InvoiceConferenceService.open(
        reconciliation(
            matched_line(),
        ),
        "CONF-001",
    )

    with pytest.raises(
        ValueError,
        match="operador",
    ):
        session.register_count(
            1,
            10,
            "",
        )


def test_nf001j_prevents_silent_recount_of_same_line():
    session = InvoiceConferenceService.open(
        reconciliation(
            matched_line(),
        ),
        "CONF-001",
    )

    session.register_count(
        1,
        10,
        "CONF-001",
    )

    with pytest.raises(
        ValueError,
        match="já possui contagem",
    ):
        session.register_count(
            1,
            11,
            "CONF-001",
        )


def test_nf001j_cannot_close_before_all_lines_are_counted():
    session = InvoiceConferenceService.open(
        reconciliation(
            matched_line(
                sku="SKU-001",
            ),
            matched_line(
                sku="SKU-002",
            ),
        ),
        "CONF-001",
    )

    session.register_count(
        1,
        10,
        "CONF-001",
    )

    assert session.can_close is False

    with pytest.raises(
        ValueError,
        match="Todas as linhas",
    ):
        InvoiceConferenceService.close(
            session,
            "CONF-001",
        )


def test_nf001j_cannot_close_with_pending_product_registration():
    session = InvoiceConferenceService.open(
        reconciliation(
            matched_line(),
            unresolved_line(),
        ),
        "CONF-001",
    )

    session.register_count(
        1,
        10,
        "CONF-001",
    )

    with pytest.raises(
        ValueError,
        match="pendentes de cadastro",
    ):
        InvoiceConferenceService.close(
            session,
            "CONF-001",
        )


def test_nf001j_explicit_close_emits_immutable_conference_evidence():
    session = InvoiceConferenceService.open(
        reconciliation(
            matched_line(
                sku="SKU-001",
                quantity=12,
            ),
            matched_line(
                sku="SKU-002",
                quantity=8,
            ),
        ),
        "CONF-OPEN",
    )

    session.register_count(
        1,
        12,
        "CONF-A",
    )

    session.register_count(
        2,
        7,
        "CONF-B",
    )

    assert session.can_close is True

    result = InvoiceConferenceService.close(
        session,
        "CONF-CLOSE",
    )

    assert session.status == ConferenceStatus.CLOSED
    assert session.closed_by == "CONF-CLOSE"

    assert result.invoice_number == "NF-001J-TEST"
    assert result.supplier_id == "SUP-001"
    assert result.closed_by == "CONF-CLOSE"
    assert result.total_lines == 2
    assert result.divergent_lines == 1

    first = result.lines[0]
    second = result.lines[1]

    assert first.product_id == "SKU-001"
    assert first.fiscal_quantity == 12
    assert first.counted_quantity == 12
    assert first.divergence == 0
    assert first.counted_by == "CONF-A"

    assert second.product_id == "SKU-002"
    assert second.fiscal_quantity == 8
    assert second.counted_quantity == 7
    assert second.divergence == -1
    assert second.counted_by == "CONF-B"


def test_nf001j_closed_session_rejects_further_mutation():
    session = InvoiceConferenceService.open(
        reconciliation(
            matched_line(),
        ),
        "CONF-001",
    )

    session.register_count(
        1,
        10,
        "CONF-001",
    )

    InvoiceConferenceService.close(
        session,
        "CONF-001",
    )

    with pytest.raises(
        ValueError,
        match="já foi encerrada",
    ):
        session.register_count(
            1,
            10,
            "CONF-001",
        )

    with pytest.raises(
        ValueError,
        match="já foi encerrada",
    ):
        InvoiceConferenceService.close(
            session,
            "CONF-001",
        )


def test_nf001j_has_no_receiving_or_stock_authority():
    signature = inspect.signature(
        InvoiceConferenceService
    )

    assert list(signature.parameters) == []

    forbidden = (
        "receive_stock",
        "receive_goods",
        "add_stock",
        "create_batch",
        "putaway",
        "register_new_product",
    )

    for name in forbidden:
        assert not hasattr(
            InvoiceConferenceService,
            name,
        )


def test_nf001j_session_requires_opening_operator():
    with pytest.raises(
        ValueError,
        match="operador",
    ):
        InvoiceConferenceService.open(
            reconciliation(
                matched_line(),
            ),
            "",
        )


def test_nf001j_empty_invoice_cannot_be_closed():
    result = CatalogReconciliationResult(
        invoice=SupplierInvoice(
            invoice_number="NF-EMPTY",
            supplier_id="SUP-001",
            lines=[],
        ),
        lines=[],
    )

    session = InvoiceConferenceService.open(
        result,
        "CONF-001",
    )

    assert session.can_close is False

    with pytest.raises(
        ValueError,
        match="sem itens",
    ):
        InvoiceConferenceService.close(
            session,
            "CONF-001",
        )
