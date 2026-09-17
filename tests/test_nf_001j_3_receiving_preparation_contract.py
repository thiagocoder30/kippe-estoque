"""
NF-001J.3 — Post-conference receiving preparation contract.
"""

import inspect

import pytest

from src.application.procurement.invoice_conference import (
    ConferenceClosedResult,
    ConferenceLineResult,
)
from src.application.procurement.receiving_preparation import (
    ReceivingPreparationService,
    ReceivingPreparationStatus,
)


def conference(
    *,
    fiscal_quantity=12,
    counted_quantity=10,
    divergence=-2,
):
    return ConferenceClosedResult(
        invoice_number="NF-J3-001",
        supplier_id="SUP-001",
        closed_by="CONF-CLOSE",
        lines=[
            ConferenceLineResult(
                line_number=1,
                product_id="SKU-001",
                fiscal_quantity=fiscal_quantity,
                counted_quantity=counted_quantity,
                divergence=divergence,
                counted_by="CONF-COUNT",
            )
        ],
    )


def test_nf001j3_preserves_conference_identity():
    source = conference()

    result = ReceivingPreparationService.prepare(source)

    assert result.invoice_number == source.invoice_number
    assert result.supplier_id == source.supplier_id
    assert (
        result.conference_closed_by
        == source.closed_by
    )


def test_nf001j3_uses_physical_count_as_receiving_quantity():
    result = ReceivingPreparationService.prepare(
        conference(
            fiscal_quantity=12,
            counted_quantity=10,
            divergence=-2,
        )
    )

    line = result.lines[0]

    assert line.fiscal_quantity == 12
    assert line.quantity_to_receive == 10
    assert line.divergence == -2


def test_nf001j3_preserves_positive_divergence_without_correcting_it():
    result = ReceivingPreparationService.prepare(
        conference(
            fiscal_quantity=10,
            counted_quantity=12,
            divergence=2,
        )
    )

    line = result.lines[0]

    assert line.quantity_to_receive == 12
    assert line.fiscal_quantity == 10
    assert line.divergence == 2


def test_nf001j3_preserves_human_attribution():
    result = ReceivingPreparationService.prepare(
        conference()
    )

    assert result.conference_closed_by == "CONF-CLOSE"
    assert result.lines[0].counted_by == "CONF-COUNT"


def test_nf001j3_nonzero_line_initially_requires_completion():
    result = ReceivingPreparationService.prepare(
        conference()
    )

    line = result.lines[0]

    assert (
        line.status
        == ReceivingPreparationStatus.NEEDS_COMPLETION
    )
    assert line.requires_human_completion is True
    assert line.is_ready is False
    assert result.pending_lines == 1
    assert result.is_ready is False


def test_nf001j3_requires_explicit_batch_code():
    result = ReceivingPreparationService.prepare(
        conference()
    )

    line = result.lines[0]

    with pytest.raises(
        ValueError,
        match="lote",
    ):
        line.complete_physical_data(
            batch_code="",
            expiration_date="2027-01-13",
        )


def test_nf001j3_requires_explicit_expiration_date():
    result = ReceivingPreparationService.prepare(
        conference()
    )

    line = result.lines[0]

    with pytest.raises(
        ValueError,
        match="validade",
    ):
        line.complete_physical_data(
            batch_code="LN2SP",
            expiration_date="",
        )


def test_nf001j3_manufacturing_date_is_optional():
    result = ReceivingPreparationService.prepare(
        conference()
    )

    line = result.lines[0]

    line.complete_physical_data(
        batch_code="LN2SP",
        expiration_date="2027-01-13",
    )

    assert line.batch_code == "LN2SP"
    assert line.expiration_date == "2027-01-13"
    assert line.manufacturing_date is None
    assert line.status == ReceivingPreparationStatus.READY


def test_nf001j3_can_preserve_explicit_manufacturing_date():
    result = ReceivingPreparationService.prepare(
        conference()
    )

    line = result.lines[0]

    line.complete_physical_data(
        batch_code="LN2SP",
        expiration_date="2027-01-13",
        manufacturing_date="2026-09-01",
    )

    assert line.manufacturing_date == "2026-09-01"
    assert line.status == ReceivingPreparationStatus.READY


def test_nf001j3_completed_line_becomes_ready():
    result = ReceivingPreparationService.prepare(
        conference()
    )

    line = result.lines[0]

    line.complete_physical_data(
        batch_code="LN2SP",
        expiration_date="2027-01-13",
    )

    assert line.status == ReceivingPreparationStatus.READY
    assert line.is_ready is True
    assert line.requires_human_completion is False

    assert result.ready_lines == 1
    assert result.pending_lines == 0
    assert result.is_ready is True


def test_nf001j3_zero_count_is_explicitly_skipped():
    result = ReceivingPreparationService.prepare(
        conference(
            fiscal_quantity=10,
            counted_quantity=0,
            divergence=-10,
        )
    )

    line = result.lines[0]

    assert line.quantity_to_receive == 0
    assert (
        line.status
        == ReceivingPreparationStatus.SKIPPED_ZERO_QUANTITY
    )
    assert line.is_zero_quantity is True
    assert result.zero_quantity_lines == 1
    assert result.pending_lines == 0


def test_nf001j3_zero_count_rejects_physical_completion():
    result = ReceivingPreparationService.prepare(
        conference(
            fiscal_quantity=10,
            counted_quantity=0,
            divergence=-10,
        )
    )

    with pytest.raises(
        ValueError,
        match="quantidade física zero",
    ):
        result.lines[0].complete_physical_data(
            batch_code="LOT-001",
            expiration_date="2027-01-01",
        )


def test_nf001j3_multiple_lines_track_readiness_independently():
    source = ConferenceClosedResult(
        invoice_number="NF-MULTI",
        supplier_id="SUP-001",
        closed_by="CONF-CLOSE",
        lines=[
            ConferenceLineResult(
                line_number=1,
                product_id="SKU-001",
                fiscal_quantity=10,
                counted_quantity=10,
                divergence=0,
                counted_by="CONF-A",
            ),
            ConferenceLineResult(
                line_number=2,
                product_id="SKU-002",
                fiscal_quantity=5,
                counted_quantity=4,
                divergence=-1,
                counted_by="CONF-B",
            ),
            ConferenceLineResult(
                line_number=3,
                product_id="SKU-003",
                fiscal_quantity=2,
                counted_quantity=0,
                divergence=-2,
                counted_by="CONF-C",
            ),
        ],
    )

    result = ReceivingPreparationService.prepare(
        source
    )

    assert result.total_lines == 3
    assert result.pending_lines == 2
    assert result.zero_quantity_lines == 1
    assert result.ready_lines == 0

    result.get_line(1).complete_physical_data(
        batch_code="L1",
        expiration_date="2027-01-01",
    )

    assert result.ready_lines == 1
    assert result.pending_lines == 1
    assert result.is_ready is False

    result.get_line(2).complete_physical_data(
        batch_code="L2",
        expiration_date="2027-02-01",
    )

    assert result.ready_lines == 2
    assert result.pending_lines == 0
    assert result.zero_quantity_lines == 1
    assert result.is_ready is True


def test_nf001j3_get_line_is_deterministic():
    result = ReceivingPreparationService.prepare(
        conference()
    )

    assert result.get_line(1) is result.lines[0]

    with pytest.raises(
        ValueError,
        match="inexistente",
    ):
        result.get_line(999)


def test_nf001j3_requires_closed_conference_evidence_type():
    with pytest.raises(
        TypeError,
        match="ConferenceClosedResult",
    ):
        ReceivingPreparationService.prepare(
            object()
        )


def test_nf001j3_rejects_negative_counted_quantity_defensively():
    source = conference(
        fiscal_quantity=10,
        counted_quantity=-1,
        divergence=-11,
    )

    with pytest.raises(
        ValueError,
        match="negativa",
    ):
        ReceivingPreparationService.prepare(
            source
        )


def test_nf001j3_has_no_receiving_or_inventory_authority():
    signature = inspect.signature(
        ReceivingPreparationService
    )

    assert list(signature.parameters) == []

    forbidden = (
        "receive",
        "receive_goods",
        "receive_stock",
        "create_batch",
        "add_stock",
        "putaway",
        "persist",
        "save",
    )

    for name in forbidden:
        assert not hasattr(
            ReceivingPreparationService,
            name,
        )
