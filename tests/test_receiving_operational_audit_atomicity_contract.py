import sqlite3

import pytest

from src.domain.product import Product
from src.interfaces.sqlite_repository import (
    SQLiteProductRepository,
)
from src.use_cases.receive_stock import ReceivingUseCase


class FailingAuditSQLiteProductRepository(
    SQLiteProductRepository
):
    def _append_operational_audit_event_on_connection(
        self,
        conn,
        **event,
    ):
        raise RuntimeError(
            "SIMULATED_AUDIT_WRITE_FAILURE"
        )


def _repository(tmp_path):
    db_path = (
        tmp_path
        / "receiving_atomicity.db"
    )

    return FailingAuditSQLiteProductRepository(
        db_path=str(db_path)
    )


def _seed_product(repository):
    product = Product(
        id="SKU-ATOMIC-001",
        name="PRODUTO TESTE ATOMICIDADE",
        ean="7890000000001",
    )

    repository.save(product)

    return product.id


def _read_product(
    repository,
    product_id,
):
    products = repository.get_all()

    return next(
        product
        for product in products
        if product.id == product_id
    )


def _audit_event_count(
    repository,
):
    with sqlite3.connect(
        repository.db_path
    ) as conn:
        return conn.execute(
            """
            SELECT COUNT(*)
            FROM operational_audit_events
            """
        ).fetchone()[0]


def _execute_receiving(
    repository,
    *,
    batch_code,
):
    use_case = ReceivingUseCase(
        repository
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "SIMULATED_AUDIT_WRITE_FAILURE"
        ),
    ):
        use_case.execute(
            identifier="7890000000001",
            quantity=10,
            batch_code=batch_code,
            expiration_date="2035-12-31",
            supplier="FORNECEDOR TESTE",
            manufacturing_date="2035-01-01",
            invoice_id="NF-ATOMIC-001",
            origin_document="MANUAL",
            operator_id="OP-ATOMIC",
        )


def test_audit_failure_rolls_back_product_quantity(
    tmp_path,
):
    repository = _repository(
        tmp_path
    )

    product_id = _seed_product(
        repository
    )

    before = _read_product(
        repository,
        product_id,
    )

    assert before.quantity == 0

    _execute_receiving(
        repository,
        batch_code="LOT-ATOMIC-QTY",
    )

    after = _read_product(
        repository,
        product_id,
    )

    assert after.quantity == 0


def test_audit_failure_rolls_back_received_batch(
    tmp_path,
):
    repository = _repository(
        tmp_path
    )

    product_id = _seed_product(
        repository
    )

    _execute_receiving(
        repository,
        batch_code="LOT-ATOMIC-BATCH",
    )

    after = _read_product(
        repository,
        product_id,
    )

    assert (
        "LOT-ATOMIC-BATCH"
        not in after.batches
    )


def test_audit_failure_leaves_no_documentary_event(
    tmp_path,
):
    repository = _repository(
        tmp_path
    )

    _seed_product(
        repository
    )

    _execute_receiving(
        repository,
        batch_code="LOT-ATOMIC-AUDIT",
    )

    assert (
        _audit_event_count(
            repository
        )
        == 0
    )
