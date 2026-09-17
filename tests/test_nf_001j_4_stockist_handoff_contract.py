"""
NF-001J.4 — Stockist Handoff Contract

The contract remains pure:
- no persistence;
- no HTTP;
- no stock mutation;
- no receiving execution;
- no batch creation;
- no putaway;
- no RBAC expansion.
"""

from dataclasses import FrozenInstanceError

import pytest

from src.application.procurement.receiving_preparation import (
    ReceivingPreparationLine,
    ReceivingPreparationResult,
)
from src.application.procurement.stockist_handoff import (
    StockistHandoffLine,
    StockistHandoffResult,
    StockistHandoffService,
    StockistHandoffStatus,
)


def preparation(
    *lines,
    invoice_number="NF-001J4",
    supplier_id="SUP-001",
    conference_closed_by="ADM-01",
):
    return ReceivingPreparationResult(
        invoice_number=invoice_number,
        supplier_id=supplier_id,
        conference_closed_by=conference_closed_by,
        lines=list(lines),
    )


def pending_line(
    *,
    line_number=1,
    product_id="SKU-001",
    fiscal_quantity=10,
    quantity_to_receive=10,
    divergence=0,
    counted_by="ADM-01",
):
    return ReceivingPreparationLine(
        line_number=line_number,
        product_id=product_id,
        fiscal_quantity=fiscal_quantity,
        quantity_to_receive=quantity_to_receive,
        divergence=divergence,
        counted_by=counted_by,
    )


def ready_line(
    *,
    line_number=1,
    product_id="SKU-001",
    fiscal_quantity=10,
    quantity_to_receive=10,
    divergence=0,
    counted_by="ADM-01",
    batch_code="LOT-001",
    expiration_date="2027-12-31",
    manufacturing_date=None,
):
    line = pending_line(
        line_number=line_number,
        product_id=product_id,
        fiscal_quantity=fiscal_quantity,
        quantity_to_receive=quantity_to_receive,
        divergence=divergence,
        counted_by=counted_by,
    )

    line.complete_physical_data(
        batch_code=batch_code,
        expiration_date=expiration_date,
        manufacturing_date=manufacturing_date,
    )

    return line


def zero_line(
    *,
    line_number=1,
    product_id="SKU-ZERO",
    fiscal_quantity=10,
    divergence=-10,
    counted_by="ADM-01",
):
    return ReceivingPreparationLine(
        line_number=line_number,
        product_id=product_id,
        fiscal_quantity=fiscal_quantity,
        quantity_to_receive=0,
        divergence=divergence,
        counted_by=counted_by,
    )


def test_requires_receiving_preparation_result():
    with pytest.raises(TypeError):
        StockistHandoffService.build(
            object(),
            completed_by="ADM-01",
        )


def test_preserves_invoice_and_conference_provenance():
    result = StockistHandoffService.build(
        preparation(
            pending_line(),
            invoice_number="NF-123",
            supplier_id="SUP-ABC",
            conference_closed_by="CONF-77",
        ),
        completed_by="EST-88",
    )

    assert result.invoice_number == "NF-123"
    assert result.supplier_id == "SUP-ABC"
    assert result.conference_closed_by == "CONF-77"


def test_pending_line_becomes_pending_physical_data():
    result = StockistHandoffService.build(
        preparation(
            pending_line(
                divergence=-2,
                counted_by="CONF-01",
            )
        ),
        completed_by="ADM-01",
    )

    line = result.lines[0]

    assert (
        line.status
        == StockistHandoffStatus.PENDING_PHYSICAL_DATA
    )
    assert line.requires_physical_completion is True
    assert line.is_ready_for_receiving is False
    assert line.completed_by is None

    assert line.divergence == -2
    assert line.counted_by == "CONF-01"


def test_ready_line_becomes_ready_for_receiving():
    result = StockistHandoffService.build(
        preparation(
            ready_line(
                batch_code="LOT-X",
                expiration_date="2028-01-31",
                manufacturing_date="2026-09-01",
            )
        ),
        completed_by="ADM-99",
    )

    line = result.lines[0]

    assert (
        line.status
        == StockistHandoffStatus.READY_FOR_RECEIVING
    )
    assert line.is_ready_for_receiving is True
    assert line.requires_physical_completion is False

    assert line.batch_code == "LOT-X"
    assert line.expiration_date == "2028-01-31"
    assert line.manufacturing_date == "2026-09-01"
    assert line.completed_by == "ADM-99"


def test_completed_by_is_normalized():
    result = StockistHandoffService.build(
        preparation(ready_line()),
        completed_by="  ADM-01  ",
    )

    assert result.lines[0].completed_by == "ADM-01"


@pytest.mark.parametrize(
    "completed_by",
    [
        None,
        "",
        "   ",
    ],
)
def test_missing_completed_by_does_not_fabricate_identity(
    completed_by,
):
    result = StockistHandoffService.build(
        preparation(ready_line()),
        completed_by=completed_by,
    )

    assert result.lines[0].completed_by is None


def test_zero_quantity_line_is_explicitly_skipped():
    result = StockistHandoffService.build(
        preparation(zero_line()),
        completed_by="ADM-01",
    )

    line = result.lines[0]

    assert (
        line.status
        == StockistHandoffStatus.SKIPPED_ZERO_QUANTITY
    )
    assert line.is_zero_quantity is True
    assert line.is_ready_for_receiving is False
    assert line.requires_physical_completion is False
    assert line.completed_by is None


def test_zero_quantity_does_not_make_result_ready():
    result = StockistHandoffService.build(
        preparation(zero_line()),
        completed_by="ADM-01",
    )

    assert result.total_lines == 1
    assert result.ready_lines == 0
    assert result.pending_lines == 0
    assert result.zero_quantity_lines == 1
    assert result.is_ready_for_receiving is False


def test_mixed_result_counts_are_deterministic():
    result = StockistHandoffService.build(
        preparation(
            ready_line(
                line_number=1,
                product_id="SKU-A",
            ),
            pending_line(
                line_number=2,
                product_id="SKU-B",
            ),
            zero_line(
                line_number=3,
                product_id="SKU-C",
            ),
        ),
        completed_by="ADM-01",
    )

    assert result.total_lines == 3
    assert result.ready_lines == 1
    assert result.pending_lines == 1
    assert result.zero_quantity_lines == 1
    assert result.is_ready_for_receiving is False


def test_all_actionable_lines_ready_makes_result_ready():
    result = StockistHandoffService.build(
        preparation(
            ready_line(
                line_number=1,
                product_id="SKU-A",
            ),
            ready_line(
                line_number=2,
                product_id="SKU-B",
            ),
            zero_line(
                line_number=3,
                product_id="SKU-C",
            ),
        ),
        completed_by="ADM-01",
    )

    assert result.ready_lines == 2
    assert result.pending_lines == 0
    assert result.zero_quantity_lines == 1
    assert result.is_ready_for_receiving is True


def test_get_line_uses_fiscal_line_identity():
    result = StockistHandoffService.build(
        preparation(
            ready_line(
                line_number=7,
                product_id="SKU-7",
            )
        ),
        completed_by="ADM-01",
    )

    assert result.get_line(7).product_id == "SKU-7"

    with pytest.raises(ValueError):
        result.get_line(999)


def test_handoff_is_snapshot_not_alias_of_preparation():
    source = ready_line(
        batch_code="LOT-ORIGINAL",
    )

    result = StockistHandoffService.build(
        preparation(source),
        completed_by="ADM-01",
    )

    source.batch_code = "LOT-MUTATED"

    assert result.lines[0].batch_code == "LOT-ORIGINAL"


def test_handoff_lines_are_immutable():
    result = StockistHandoffService.build(
        preparation(ready_line()),
        completed_by="ADM-01",
    )

    with pytest.raises(FrozenInstanceError):
        result.lines[0].batch_code = "OTHER"


def test_line_contract_preserves_receiving_mapping_fields():
    result = StockistHandoffService.build(
        preparation(
            ready_line(
                product_id="SKU-MAP",
                quantity_to_receive=17,
                batch_code="LOT-MAP",
                expiration_date="2029-02-03",
                manufacturing_date="2026-08-04",
            ),
            supplier_id="SUP-MAP",
            invoice_number="NF-MAP",
        ),
        completed_by="ADM-MAP",
    )

    line = result.lines[0]

    assert line.product_id == "SKU-MAP"
    assert line.quantity_to_receive == 17
    assert line.batch_code == "LOT-MAP"
    assert line.expiration_date == "2029-02-03"
    assert line.manufacturing_date == "2026-08-04"

    assert result.supplier_id == "SUP-MAP"
    assert result.invoice_number == "NF-MAP"
    assert line.completed_by == "ADM-MAP"


def test_handoff_does_not_define_location_or_warehouse():
    annotations = StockistHandoffLine.__annotations__

    assert "location_id" not in annotations
    assert "warehouse_id" not in annotations


def test_handoff_does_not_introduce_role_field():
    assert "role" not in StockistHandoffLine.__annotations__
    assert "role" not in StockistHandoffResult.__annotations__


def test_status_values_are_explicit_and_stable():
    assert [
        item.value
        for item in StockistHandoffStatus
    ] == [
        "PENDING_PHYSICAL_DATA",
        "READY_FOR_RECEIVING",
        "SKIPPED_ZERO_QUANTITY",
    ]
