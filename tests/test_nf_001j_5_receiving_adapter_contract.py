"""
NF-001J.5 — Pure Receiving Adapter contract.
"""

from dataclasses import FrozenInstanceError
import inspect

import pytest

from src.application.procurement.receiving_adapter import (
    ReceivingAdapter,
    ReceivingCommand,
)
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


def ready_handoff(
    *,
    line_number=1,
    product_id="SKU-001",
    fiscal_quantity=12,
    quantity_to_receive=10,
    divergence=-2,
    counted_by="ADM-CONFERENCE",
    batch_code="LOT-001",
    expiration_date="2027-12-31",
    manufacturing_date=None,
    supplier_id="SUP-001",
    invoice_number="NF-001",
    conference_closed_by="ADM-CONFERENCE",
    completed_by="ADM-STOCKIST",
):
    preparation_line = ReceivingPreparationLine(
        line_number=line_number,
        product_id=product_id,
        fiscal_quantity=fiscal_quantity,
        quantity_to_receive=quantity_to_receive,
        divergence=divergence,
        counted_by=counted_by,
    )

    preparation_line.complete_physical_data(
        batch_code=batch_code,
        expiration_date=expiration_date,
        manufacturing_date=manufacturing_date,
    )

    preparation = ReceivingPreparationResult(
        invoice_number=invoice_number,
        supplier_id=supplier_id,
        conference_closed_by=conference_closed_by,
        lines=[preparation_line],
    )

    return StockistHandoffService.build(
        preparation,
        completed_by=completed_by,
    )


def pending_handoff():
    preparation = ReceivingPreparationResult(
        invoice_number="NF-PENDING",
        supplier_id="SUP-PENDING",
        conference_closed_by="ADM-CONFERENCE",
        lines=[
            ReceivingPreparationLine(
                line_number=1,
                product_id="SKU-PENDING",
                fiscal_quantity=10,
                quantity_to_receive=10,
                divergence=0,
                counted_by="ADM-CONFERENCE",
            )
        ],
    )

    return StockistHandoffService.build(
        preparation,
        completed_by="ADM-STOCKIST",
    )


def zero_handoff():
    preparation = ReceivingPreparationResult(
        invoice_number="NF-ZERO",
        supplier_id="SUP-ZERO",
        conference_closed_by="ADM-CONFERENCE",
        lines=[
            ReceivingPreparationLine(
                line_number=1,
                product_id="SKU-ZERO",
                fiscal_quantity=10,
                quantity_to_receive=0,
                divergence=-10,
                counted_by="ADM-CONFERENCE",
            )
        ],
    )

    return StockistHandoffService.build(
        preparation,
        completed_by="ADM-STOCKIST",
    )


def replace_line(
    handoff,
    **changes,
):
    source = handoff.lines[0]

    values = {
        field: getattr(source, field)
        for field in StockistHandoffLine.__annotations__
    }

    values.update(changes)

    replacement = StockistHandoffLine(
        **values
    )

    return StockistHandoffResult(
        invoice_number=handoff.invoice_number,
        supplier_id=handoff.supplier_id,
        conference_closed_by=(
            handoff.conference_closed_by
        ),
        lines=[replacement],
    )


def test_adapter_requires_handoff_result():
    with pytest.raises(
        TypeError,
        match="StockistHandoffResult",
    ):
        ReceivingAdapter.build_command(
            object(),
            line_number=1,
        )


def test_adapter_maps_all_certified_receiving_fields():
    handoff = ready_handoff(
        product_id="SKU-MAP",
        quantity_to_receive=17,
        batch_code="LOT-MAP",
        expiration_date="2029-02-03",
        manufacturing_date="2026-08-04",
        supplier_id="SUP-MAP",
        invoice_number="NF-MAP",
        completed_by="ADM-MAP",
    )

    command = ReceivingAdapter.build_command(
        handoff,
        line_number=1,
    )

    assert command.identifier == "SKU-MAP"
    assert command.quantity == 17
    assert command.batch_code == "LOT-MAP"
    assert command.expiration_date == "2029-02-03"
    assert command.supplier == "SUP-MAP"
    assert command.manufacturing_date == "2026-08-04"
    assert command.invoice_id == "NF-MAP"
    assert command.origin_document == "SUPPLIER_INVOICE"
    assert command.operator_id == "ADM-MAP"


def test_command_field_order_matches_receiving_use_case_contract():
    assert list(
        ReceivingCommand.__annotations__
    ) == [
        "identifier",
        "quantity",
        "batch_code",
        "expiration_date",
        "supplier",
        "manufacturing_date",
        "invoice_id",
        "origin_document",
        "operator_id",
    ]


def test_command_is_immutable():
    command = ReceivingAdapter.build_command(
        ready_handoff(),
        line_number=1,
    )

    with pytest.raises(FrozenInstanceError):
        command.quantity = 999


def test_manufacturing_date_maps_none_to_empty_string():
    command = ReceivingAdapter.build_command(
        ready_handoff(
            manufacturing_date=None,
        ),
        line_number=1,
    )

    assert command.manufacturing_date == ""


def test_adapter_uses_requested_fiscal_line_number():
    first = ready_handoff(
        line_number=7,
        product_id="SKU-7",
    )

    command = ReceivingAdapter.build_command(
        first,
        line_number=7,
    )

    assert command.identifier == "SKU-7"


def test_unknown_line_is_rejected():
    with pytest.raises(
        ValueError,
        match="inexistente",
    ):
        ReceivingAdapter.build_command(
            ready_handoff(),
            line_number=999,
        )


def test_pending_physical_data_is_rejected():
    handoff = pending_handoff()

    assert (
        handoff.lines[0].status
        == StockistHandoffStatus.PENDING_PHYSICAL_DATA
    )

    with pytest.raises(
        ValueError,
        match="READY_FOR_RECEIVING",
    ):
        ReceivingAdapter.build_command(
            handoff,
            line_number=1,
        )


def test_zero_quantity_line_is_rejected():
    handoff = zero_handoff()

    assert (
        handoff.lines[0].status
        == StockistHandoffStatus.SKIPPED_ZERO_QUANTITY
    )

    with pytest.raises(
        ValueError,
        match="READY_FOR_RECEIVING",
    ):
        ReceivingAdapter.build_command(
            handoff,
            line_number=1,
        )


def test_ready_status_with_zero_quantity_is_defensively_rejected():
    handoff = replace_line(
        ready_handoff(),
        quantity_to_receive=0,
    )

    with pytest.raises(
        ValueError,
        match="maior que zero",
    ):
        ReceivingAdapter.build_command(
            handoff,
            line_number=1,
        )


@pytest.mark.parametrize(
    "field,value,expected",
    [
        ("product_id", "", "product_id"),
        ("batch_code", "", "batch_code"),
        (
            "expiration_date",
            None,
            "expiration_date",
        ),
        (
            "completed_by",
            None,
            "completed_by",
        ),
    ],
)
def test_required_line_fields_are_revalidated(
    field,
    value,
    expected,
):
    handoff = replace_line(
        ready_handoff(),
        **{field: value},
    )

    with pytest.raises(
        ValueError,
        match=expected,
    ):
        ReceivingAdapter.build_command(
            handoff,
            line_number=1,
        )


def test_supplier_is_required():
    source = ready_handoff()

    handoff = StockistHandoffResult(
        invoice_number=source.invoice_number,
        supplier_id="",
        conference_closed_by=(
            source.conference_closed_by
        ),
        lines=source.lines,
    )

    with pytest.raises(
        ValueError,
        match="supplier_id",
    ):
        ReceivingAdapter.build_command(
            handoff,
            line_number=1,
        )


def test_invoice_number_is_required():
    source = ready_handoff()

    handoff = StockistHandoffResult(
        invoice_number="",
        supplier_id=source.supplier_id,
        conference_closed_by=(
            source.conference_closed_by
        ),
        lines=source.lines,
    )

    with pytest.raises(
        ValueError,
        match="invoice_number",
    ):
        ReceivingAdapter.build_command(
            handoff,
            line_number=1,
        )


def test_adapter_preserves_handoff_without_mutation():
    handoff = ready_handoff()

    before = handoff.lines[0]

    command = ReceivingAdapter.build_command(
        handoff,
        line_number=1,
    )

    after = handoff.lines[0]

    assert before is after
    assert after.quantity_to_receive == 10
    assert after.batch_code == "LOT-001"
    assert command.quantity == 10


def test_build_line_command_requires_line_contract():
    with pytest.raises(
        TypeError,
        match="StockistHandoffLine",
    ):
        ReceivingAdapter.build_line_command(
            ready_handoff(),
            object(),
        )


def test_adapter_constructor_requires_no_dependencies():
    assert list(
        inspect.signature(
            ReceivingAdapter
        ).parameters
    ) == []


def test_adapter_exposes_no_execution_authority():
    forbidden = (
        "execute",
        "receive",
        "receive_stock",
        "receive_goods",
        "persist",
        "save",
        "create_batch",
        "putaway",
    )

    for name in forbidden:
        assert not hasattr(
            ReceivingAdapter,
            name,
        )


def test_command_contains_no_location_or_role_authority():
    fields = ReceivingCommand.__annotations__

    assert "location_id" not in fields
    assert "warehouse_id" not in fields
    assert "role" not in fields


def test_origin_document_is_stable_domain_provenance():
    command = ReceivingAdapter.build_command(
        ready_handoff(
            invoice_number="NF-777",
        ),
        line_number=1,
    )

    assert command.invoice_id == "NF-777"
    assert command.origin_document == "SUPPLIER_INVOICE"
