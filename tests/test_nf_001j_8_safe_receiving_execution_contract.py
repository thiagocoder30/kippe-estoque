"""
NF-001J.8 — Safe Receiving Execution contract.
"""

import sqlite3

import pytest

from src.application.procurement.receiving_adapter import (
    ReceivingAdapter,
)
from src.application.procurement.receiving_execution import (
    SafeReceivingExecutionService,
)
from src.application.procurement.receiving_identity import (
    ReceivingIdentityService,
    ReceivingReplayStatus,
)
from src.application.procurement.receiving_preparation import (
    ReceivingPreparationLine,
    ReceivingPreparationResult,
)
from src.application.procurement.stockist_handoff import (
    StockistHandoffService,
)
from src.domain.product import Product
from src.interfaces.sqlite_repository import (
    SQLiteProductRepository,
)


class FailingJ8AuditRepository(
    SQLiteProductRepository
):
    def _append_operational_audit_event_on_connection(
        self,
        conn,
        **event,
    ):
        raise RuntimeError(
            "SIMULATED_J8_AUDIT_FAILURE"
        )


def build_context(
    repository,
    *,
    quantity=12,
    batch_code="LOT-J8",
):
    product = Product(
        id="SKU-J8",
        name="PRODUTO J8",
        ean="7890000008001",
    )

    repository.save(product)

    line = ReceivingPreparationLine(
        line_number=1,
        product_id="SKU-J8",
        fiscal_quantity=quantity,
        quantity_to_receive=quantity,
        divergence=0,
        counted_by="ADM-CONFERENCE",
    )

    line.complete_physical_data(
        batch_code=batch_code,
        expiration_date="2027-12-31",
        manufacturing_date="2026-09-01",
    )

    preparation = ReceivingPreparationResult(
        invoice_number="NF-J8",
        supplier_id="SUP-J8",
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

    envelope = ReceivingIdentityService.build(
        handoff,
        line_number=1,
        command=command,
    )

    return envelope, command


def execute(repository, envelope, command):
    return SafeReceivingExecutionService.execute(
        repository,
        envelope,
        identifier=command.identifier,
        quantity=command.quantity,
        batch_code=command.batch_code,
        expiration_date=command.expiration_date,
        supplier=command.supplier,
        manufacturing_date=(
            command.manufacturing_date
        ),
        invoice_id=command.invoice_id,
        operator_id=command.operator_id,
    )


def quantity(repository):
    product = next(
        product
        for product in repository.get_all()
        if product.id == "SKU-J8"
    )

    return product.quantity


def test_first_execution_changes_stock_once(
    tmp_path,
):
    repository = SQLiteProductRepository(
        db_path=str(tmp_path / "j8.db")
    )

    envelope, command = build_context(
        repository
    )

    result = execute(
        repository,
        envelope,
        command,
    )

    assert result.executed is True
    assert (
        result.decision.status
        == ReceivingReplayStatus.NEW
    )
    assert result.operation_status == "COMPLETED"
    assert quantity(repository) == 12


def test_replay_never_changes_stock_twice(
    tmp_path,
):
    repository = SQLiteProductRepository(
        db_path=str(tmp_path / "j8.db")
    )

    envelope, command = build_context(
        repository
    )

    first = execute(
        repository,
        envelope,
        command,
    )

    second = execute(
        repository,
        envelope,
        command,
    )

    assert first.executed is True
    assert second.executed is False
    assert (
        second.decision.status
        == ReceivingReplayStatus.REPLAY
    )
    assert quantity(repository) == 12


def test_operation_is_completed_with_stock_commit(
    tmp_path,
):
    repository = SQLiteProductRepository(
        db_path=str(tmp_path / "j8.db")
    )

    envelope, command = build_context(
        repository
    )

    execute(
        repository,
        envelope,
        command,
    )

    operation = repository.get_receiving_operation(
        envelope.idempotency_key
    )

    assert operation is not None
    assert operation["status"] == "COMPLETED"


def test_audit_failure_rolls_back_everything(
    tmp_path,
):
    repository = FailingJ8AuditRepository(
        db_path=str(tmp_path / "j8.db")
    )

    envelope, command = build_context(
        repository
    )

    with pytest.raises(
        RuntimeError,
        match="SIMULATED_J8_AUDIT_FAILURE",
    ):
        execute(
            repository,
            envelope,
            command,
        )

    assert quantity(repository) == 0

    operation = repository.get_receiving_operation(
        envelope.idempotency_key
    )

    assert operation is None

    with sqlite3.connect(
        repository.db_path
    ) as conn:
        audit_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM operational_audit_events
            """
        ).fetchone()[0]

    assert audit_count == 0


def test_restart_preserves_replay_protection(
    tmp_path,
):
    db_path = str(tmp_path / "j8.db")

    first_repository = SQLiteProductRepository(
        db_path=db_path
    )

    envelope, command = build_context(
        first_repository
    )

    first = execute(
        first_repository,
        envelope,
        command,
    )

    assert first.executed is True

    restarted_repository = SQLiteProductRepository(
        db_path=db_path
    )

    replay = execute(
        restarted_repository,
        envelope,
        command,
    )

    assert replay.executed is False
    assert (
        replay.decision.status
        == ReceivingReplayStatus.REPLAY
    )
    assert quantity(restarted_repository) == 12


def test_conflict_never_changes_stock(
    tmp_path,
):
    repository = SQLiteProductRepository(
        db_path=str(tmp_path / "j8.db")
    )

    envelope, command = build_context(
        repository,
        quantity=12,
    )

    execute(
        repository,
        envelope,
        command,
    )

    changed_line = ReceivingPreparationLine(
        line_number=1,
        product_id="SKU-J8",
        fiscal_quantity=12,
        quantity_to_receive=11,
        divergence=-1,
        counted_by="ADM-CONFERENCE",
    )

    changed_line.complete_physical_data(
        batch_code="LOT-J8",
        expiration_date="2027-12-31",
        manufacturing_date="2026-09-01",
    )

    changed_preparation = ReceivingPreparationResult(
        invoice_number="NF-J8",
        supplier_id="SUP-J8",
        conference_closed_by="ADM-CONFERENCE",
        lines=[changed_line],
    )

    changed_handoff = StockistHandoffService.build(
        changed_preparation,
        completed_by="ADM-STOCKIST",
    )

    changed_command = ReceivingAdapter.build_command(
        changed_handoff,
        line_number=1,
    )

    changed_envelope = ReceivingIdentityService.build(
        changed_handoff,
        line_number=1,
        command=changed_command,
    )

    result = execute(
        repository,
        changed_envelope,
        changed_command,
    )

    assert result.executed is False
    assert (
        result.decision.status
        == ReceivingReplayStatus.CONFLICT
    )
    assert quantity(repository) == 12
