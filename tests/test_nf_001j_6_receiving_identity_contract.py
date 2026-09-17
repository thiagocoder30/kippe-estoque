"""
NF-001J.6 — Deterministic Receiving Identity Contract.
"""

from dataclasses import FrozenInstanceError, replace

import pytest

from src.application.procurement.receiving_adapter import (
    ReceivingAdapter,
    ReceivingCommand,
)
from src.application.procurement.receiving_identity import (
    ReceivingIdentity,
    ReceivingIdentityEnvelope,
    ReceivingIdentityService,
    ReceivingReplayDecision,
    ReceivingReplayStatus,
)
from src.application.procurement.receiving_preparation import (
    ReceivingPreparationLine,
    ReceivingPreparationResult,
)
from src.application.procurement.stockist_handoff import (
    StockistHandoffResult,
    StockistHandoffService,
)


def build_ready(
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
    completed_by="ADM-STOCKIST",
):
    line = ReceivingPreparationLine(
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

    preparation = ReceivingPreparationResult(
        invoice_number=invoice_number,
        supplier_id=supplier_id,
        conference_closed_by="ADM-CONFERENCE",
        lines=[line],
    )

    handoff = StockistHandoffService.build(
        preparation,
        completed_by=completed_by,
    )

    command = ReceivingAdapter.build_command(
        handoff,
        line_number=line_number,
    )

    return handoff, command


def build_envelope(**kwargs):
    handoff, command = build_ready(**kwargs)

    return ReceivingIdentityService.build(
        handoff,
        line_number=kwargs.get("line_number", 1),
        command=command,
    )


def test_identity_is_deterministic():
    first = build_envelope()
    second = build_envelope()

    assert first.identity == second.identity
    assert first.idempotency_key == second.idempotency_key
    assert first.fingerprint == second.fingerprint


def test_identity_contains_fiscal_line_coordinates():
    envelope = build_envelope(
        supplier_id="SUP-X",
        invoice_number="NF-777",
        line_number=9,
    )

    assert envelope.identity == ReceivingIdentity(
        origin_document="SUPPLIER_INVOICE",
        supplier_id="SUP-X",
        invoice_number="NF-777",
        line_number=9,
    )

    assert envelope.idempotency_key == (
        "SUPPLIER_INVOICE|SUP-X|NF-777|9"
    )


def test_different_lines_have_different_identity():
    first = build_envelope(
        line_number=1,
    )

    second = build_envelope(
        line_number=2,
    )

    assert first.identity != second.identity
    assert first.idempotency_key != second.idempotency_key


def test_same_product_and_batch_on_different_lines_remain_distinct():
    first = build_envelope(
        line_number=1,
        product_id="SKU-SAME",
        batch_code="LOT-SAME",
    )

    second = build_envelope(
        line_number=2,
        product_id="SKU-SAME",
        batch_code="LOT-SAME",
    )

    assert first.idempotency_key != second.idempotency_key


def test_same_invoice_number_from_different_supplier_is_distinct():
    first = build_envelope(
        supplier_id="SUP-A",
        invoice_number="123",
    )

    second = build_envelope(
        supplier_id="SUP-B",
        invoice_number="123",
    )

    assert first.idempotency_key != second.idempotency_key


def test_identical_payload_has_identical_fingerprint():
    first = build_envelope(
        manufacturing_date="2026-09-01",
    )

    second = build_envelope(
        manufacturing_date="2026-09-01",
    )

    assert first.fingerprint == second.fingerprint
    assert len(first.fingerprint) == 64


@pytest.mark.parametrize(
    "field,first_value,second_value",
    [
        ("quantity_to_receive", 10, 11),
        ("batch_code", "LOT-A", "LOT-B"),
        (
            "expiration_date",
            "2027-12-31",
            "2028-01-01",
        ),
        (
            "manufacturing_date",
            "2026-01-01",
            "2026-01-02",
        ),
        ("product_id", "SKU-A", "SKU-B"),
        ("counted_by", "CONF-A", "CONF-B"),
        ("completed_by", "EST-A", "EST-B"),
    ],
)
def test_payload_changes_change_fingerprint(
    field,
    first_value,
    second_value,
):
    first = build_envelope(
        **{field: first_value}
    )

    second = build_envelope(
        **{field: second_value}
    )

    assert first.fingerprint != second.fingerprint


def test_compare_without_previous_fingerprint_is_new():
    envelope = build_envelope()

    decision = ReceivingIdentityService.compare(
        envelope,
        previous_fingerprint=None,
    )

    assert decision.status == ReceivingReplayStatus.NEW
    assert decision.may_execute is True
    assert decision.is_safe_replay is False
    assert decision.is_conflict is False


def test_compare_same_fingerprint_is_replay():
    envelope = build_envelope()

    decision = ReceivingIdentityService.compare(
        envelope,
        previous_fingerprint=envelope.fingerprint,
    )

    assert decision.status == ReceivingReplayStatus.REPLAY
    assert decision.may_execute is False
    assert decision.is_safe_replay is True
    assert decision.is_conflict is False


def test_compare_different_fingerprint_is_conflict():
    envelope = build_envelope()

    decision = ReceivingIdentityService.compare(
        envelope,
        previous_fingerprint="f" * 64,
    )

    assert decision.status == ReceivingReplayStatus.CONFLICT
    assert decision.may_execute is False
    assert decision.is_safe_replay is False
    assert decision.is_conflict is True


def test_empty_previous_fingerprint_means_no_previous_operation():
    envelope = build_envelope()

    decision = ReceivingIdentityService.compare(
        envelope,
        previous_fingerprint="   ",
    )

    assert decision.status == ReceivingReplayStatus.NEW


def test_identity_contracts_are_immutable():
    envelope = build_envelope()

    with pytest.raises(FrozenInstanceError):
        envelope.identity.invoice_number = "OTHER"

    with pytest.raises(FrozenInstanceError):
        envelope.fingerprint = "OTHER"


def test_build_requires_handoff_contract():
    _, command = build_ready()

    with pytest.raises(TypeError):
        ReceivingIdentityService.build(
            object(),
            line_number=1,
            command=command,
        )


def test_build_requires_receiving_command():
    handoff, _ = build_ready()

    with pytest.raises(TypeError):
        ReceivingIdentityService.build(
            handoff,
            line_number=1,
            command=object(),
        )


def test_command_must_match_certified_handoff_product():
    handoff, command = build_ready()

    divergent = replace(
        command,
        identifier="SKU-OTHER",
    )

    with pytest.raises(
        ValueError,
        match="identifier",
    ):
        ReceivingIdentityService.build(
            handoff,
            line_number=1,
            command=divergent,
        )


def test_command_must_match_certified_handoff_quantity():
    handoff, command = build_ready()

    divergent = replace(
        command,
        quantity=999,
    )

    with pytest.raises(
        ValueError,
        match="quantity",
    ):
        ReceivingIdentityService.build(
            handoff,
            line_number=1,
            command=divergent,
        )


def test_command_must_match_certified_invoice():
    handoff, command = build_ready()

    divergent = replace(
        command,
        invoice_id="NF-OTHER",
    )

    with pytest.raises(
        ValueError,
        match="invoice_id",
    ):
        ReceivingIdentityService.build(
            handoff,
            line_number=1,
            command=divergent,
        )


def test_command_must_match_certified_supplier():
    handoff, command = build_ready()

    divergent = replace(
        command,
        supplier="SUP-OTHER",
    )

    with pytest.raises(
        ValueError,
        match="supplier",
    ):
        ReceivingIdentityService.build(
            handoff,
            line_number=1,
            command=divergent,
        )


def test_command_must_match_stockist_operator():
    handoff, command = build_ready()

    divergent = replace(
        command,
        operator_id="OTHER",
    )

    with pytest.raises(
        ValueError,
        match="operator_id",
    ):
        ReceivingIdentityService.build(
            handoff,
            line_number=1,
            command=divergent,
        )


def test_compare_requires_envelope():
    with pytest.raises(TypeError):
        ReceivingIdentityService.compare(
            object(),
            previous_fingerprint=None,
        )


def test_replay_decision_preserves_identity_and_fingerprints():
    envelope = build_envelope()

    decision = ReceivingIdentityService.compare(
        envelope,
        previous_fingerprint="a" * 64,
    )

    assert isinstance(
        decision,
        ReceivingReplayDecision,
    )
    assert decision.identity == envelope.identity
    assert decision.current_fingerprint == envelope.fingerprint
    assert decision.previous_fingerprint == "a" * 64


def test_envelope_preserves_original_command_snapshot():
    handoff, command = build_ready()

    envelope = ReceivingIdentityService.build(
        handoff,
        line_number=1,
        command=command,
    )

    assert envelope.command is command


def test_identity_does_not_use_batch_as_operation_identity():
    first = build_envelope(
        batch_code="LOT-A",
    )

    second = build_envelope(
        batch_code="LOT-B",
    )

    assert first.idempotency_key == second.idempotency_key
    assert first.fingerprint != second.fingerprint


def test_identity_does_not_use_product_as_operation_identity():
    first = build_envelope(
        product_id="SKU-A",
    )

    second = build_envelope(
        product_id="SKU-B",
    )

    assert first.idempotency_key == second.idempotency_key
    assert first.fingerprint != second.fingerprint


def test_status_values_are_stable():
    assert [
        item.value
        for item in ReceivingReplayStatus
    ] == [
        "NEW",
        "REPLAY",
        "CONFLICT",
    ]


def test_identity_contract_contains_no_database_coordinates():
    fields = ReceivingIdentity.__annotations__

    assert "database_id" not in fields
    assert "event_id" not in fields
    assert "transaction_id" not in fields


def test_envelope_contains_no_execution_authority():
    forbidden = (
        "execute",
        "receive",
        "persist",
        "save",
        "commit",
        "rollback",
    )

    for name in forbidden:
        assert not hasattr(
            ReceivingIdentityEnvelope,
            name,
        )
