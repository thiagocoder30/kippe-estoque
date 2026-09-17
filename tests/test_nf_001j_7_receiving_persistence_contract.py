"""
NF-001J.7 — Receiving Persistence / Atomicity Contract.
"""

import sqlite3
from concurrent.futures import ThreadPoolExecutor

from src.application.procurement.receiving_adapter import (
    ReceivingAdapter,
)
from src.application.procurement.receiving_identity import (
    ReceivingIdentityService,
    ReceivingReplayStatus,
)
from src.application.procurement.receiving_persistence import (
    ReceivingPersistenceService,
)
from src.application.procurement.receiving_preparation import (
    ReceivingPreparationLine,
    ReceivingPreparationResult,
)
from src.application.procurement.stockist_handoff import (
    StockistHandoffService,
)
from src.interfaces.sqlite_repository import (
    SQLiteProductRepository,
)


def build_envelope(
    *,
    quantity_to_receive=10,
    batch_code="LOT-J7",
):
    line = ReceivingPreparationLine(
        line_number=1,
        product_id="SKU-J7",
        fiscal_quantity=12,
        quantity_to_receive=quantity_to_receive,
        divergence=quantity_to_receive - 12,
        counted_by="ADM-CONFERENCE",
    )

    line.complete_physical_data(
        batch_code=batch_code,
        expiration_date="2027-12-31",
        manufacturing_date="2026-09-01",
    )

    preparation = ReceivingPreparationResult(
        invoice_number="NF-J7",
        supplier_id="SUP-J7",
        conference_closed_by="ADM-CONFERENCE",
        lines=[line],
    )

    handoff = StockistHandoffService.build(
        preparation,
        completed_by="ADM-STOCKIST",
    )

    command = ReceivingAdapter.build_command(
        handoff,
        line_number=1,
    )

    return ReceivingIdentityService.build(
        handoff,
        line_number=1,
        command=command,
    )


def repository(tmp_path):
    return SQLiteProductRepository(
        db_path=str(
            tmp_path / "j7.db"
        )
    )


def test_bootstrap_creates_receiving_operations_table(
    tmp_path,
):
    repo = repository(tmp_path)

    with sqlite3.connect(repo.db_path) as conn:
        row = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'receiving_operations'
            """
        ).fetchone()

    assert row is not None


def test_first_claim_is_new_and_persisted(
    tmp_path,
):
    repo = repository(tmp_path)
    envelope = build_envelope()

    result = ReceivingPersistenceService.claim(
        repo,
        envelope,
    )

    assert (
        result.decision.status
        == ReceivingReplayStatus.NEW
    )
    assert result.may_execute is True
    assert result.operation_status == "CLAIMED"

    stored = repo.get_receiving_operation(
        envelope.idempotency_key
    )

    assert stored is not None
    assert (
        stored["fingerprint"]
        == envelope.fingerprint
    )
    assert stored["status"] == "CLAIMED"


def test_identical_retry_is_safe_replay(
    tmp_path,
):
    repo = repository(tmp_path)
    envelope = build_envelope()

    first = ReceivingPersistenceService.claim(
        repo,
        envelope,
    )
    second = ReceivingPersistenceService.claim(
        repo,
        envelope,
    )

    assert (
        first.decision.status
        == ReceivingReplayStatus.NEW
    )
    assert (
        second.decision.status
        == ReceivingReplayStatus.REPLAY
    )
    assert second.may_execute is False
    assert (
        second.decision.previous_fingerprint
        == envelope.fingerprint
    )


def test_same_identity_with_changed_payload_is_conflict(
    tmp_path,
):
    repo = repository(tmp_path)

    first = build_envelope(
        quantity_to_receive=10,
    )
    changed = build_envelope(
        quantity_to_receive=11,
    )

    assert (
        first.idempotency_key
        == changed.idempotency_key
    )
    assert (
        first.fingerprint
        != changed.fingerprint
    )

    ReceivingPersistenceService.claim(
        repo,
        first,
    )

    result = ReceivingPersistenceService.claim(
        repo,
        changed,
    )

    assert (
        result.decision.status
        == ReceivingReplayStatus.CONFLICT
    )
    assert result.may_execute is False
    assert (
        result.decision.previous_fingerprint
        == first.fingerprint
    )


def test_claim_does_not_mutate_products_batches_or_transactions(
    tmp_path,
):
    repo = repository(tmp_path)
    envelope = build_envelope()

    with sqlite3.connect(repo.db_path) as conn:
        before = {
            table: conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            for table in (
                "products",
                "batches",
                "transactions",
                "operational_audit_events",
            )
        }

    ReceivingPersistenceService.claim(
        repo,
        envelope,
    )

    with sqlite3.connect(repo.db_path) as conn:
        after = {
            table: conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            for table in (
                "products",
                "batches",
                "transactions",
                "operational_audit_events",
            )
        }

    assert after == before


def test_concurrent_identical_claim_has_single_new_authority(
    tmp_path,
):
    repo = repository(tmp_path)
    envelope = build_envelope()

    def claim():
        return ReceivingPersistenceService.claim(
            repo,
            envelope,
        ).decision.status

    with ThreadPoolExecutor(
        max_workers=8
    ) as executor:
        statuses = list(
            executor.map(
                lambda _: claim(),
                range(8),
            )
        )

    assert (
        statuses.count(
            ReceivingReplayStatus.NEW
        )
        == 1
    )
    assert (
        statuses.count(
            ReceivingReplayStatus.REPLAY
        )
        == 7
    )

    with sqlite3.connect(repo.db_path) as conn:
        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM receiving_operations
            """
        ).fetchone()[0]

    assert count == 1


def test_concurrent_conflicting_payload_never_creates_second_claim(
    tmp_path,
):
    repo = repository(tmp_path)

    original = build_envelope(
        quantity_to_receive=10,
    )
    changed = build_envelope(
        quantity_to_receive=11,
    )

    first = ReceivingPersistenceService.claim(
        repo,
        original,
    )

    assert (
        first.decision.status
        == ReceivingReplayStatus.NEW
    )

    def claim_changed():
        return ReceivingPersistenceService.claim(
            repo,
            changed,
        ).decision.status

    with ThreadPoolExecutor(
        max_workers=6
    ) as executor:
        statuses = list(
            executor.map(
                lambda _: claim_changed(),
                range(6),
            )
        )

    assert statuses == [
        ReceivingReplayStatus.CONFLICT
    ] * 6

    stored = repo.get_receiving_operation(
        original.idempotency_key
    )

    assert (
        stored["fingerprint"]
        == original.fingerprint
    )


def test_claim_requires_identity_envelope(
    tmp_path,
):
    repo = repository(tmp_path)

    try:
        ReceivingPersistenceService.claim(
            repo,
            object(),
        )
    except TypeError as exc:
        assert (
            "ReceivingIdentityEnvelope"
            in str(exc)
        )
    else:
        raise AssertionError(
            "TypeError was not raised."
        )


def test_repository_claim_validates_required_key(
    tmp_path,
):
    repo = repository(tmp_path)

    try:
        repo.claim_receiving_operation(
            idempotency_key="",
            fingerprint="f" * 64,
            origin_document="SUPPLIER_INVOICE",
            supplier_id="SUP-J7",
            invoice_number="NF-J7",
            line_number=1,
        )
    except ValueError as exc:
        assert "idempotency_key" in str(exc)
    else:
        raise AssertionError(
            "ValueError was not raised."
        )


def test_receiving_operation_identity_is_primary_key(
    tmp_path,
):
    repo = repository(tmp_path)

    with sqlite3.connect(repo.db_path) as conn:
        columns = conn.execute(
            """
            PRAGMA table_info(receiving_operations)
            """
        ).fetchall()

    by_name = {
        column[1]: column
        for column in columns
    }

    assert (
        by_name["idempotency_key"][5]
        == 1
    )


def test_j7_service_contains_no_receiving_execution_authority():
    forbidden = (
        "execute",
        "receive",
        "putaway",
    )

    for name in forbidden:
        assert not hasattr(
            ReceivingPersistenceService,
            name,
        )
