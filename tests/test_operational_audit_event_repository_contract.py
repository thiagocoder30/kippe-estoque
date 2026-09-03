import json
import sqlite3

from src.interfaces.sqlite_repository import SQLiteProductRepository


AUDIT_TABLE = "operational_audit_events"


def _repository(tmp_path):
    db_path = tmp_path / "product_audit.db"

    repository = SQLiteProductRepository(
        str(db_path)
    )

    return repository, db_path


def _table_columns(db_path):
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            f'PRAGMA table_info("{AUDIT_TABLE}")'
        ).fetchall()

    return {
        row[1]: row
        for row in rows
    }


def _insert_product(
    repository,
    *,
    name="PRODUTO TESTE AUDITORIA",
    ean="7890000000001",
):
    repository.register_new_product(
        name=name,
        ean=ean,
        unit_of_measure="un",
        status="ATIVO",
        category_id=None,
    )

    product = repository.get_by_ean(
        ean
    )

    assert product is not None

    return product


def _append_event(
    repository,
    *,
    product_id="SKU000001",
    event_type="RECEBIMENTO",
    batch_code="LOT-001",
    location_id="",
    quantity_planned=None,
    quantity_actual=10,
    quantity_before=0,
    quantity_after=10,
    quantity_divergence=None,
    supplier="FORNECEDOR TESTE",
    document_id="NF-123",
    origin_document="MANUAL",
    operator_id="OP-001",
    metadata=None,
):
    return (
        repository
        .append_operational_audit_event(
            event_type=event_type,
            product_id=product_id,
            batch_code=batch_code,
            location_id=location_id,
            quantity_planned=quantity_planned,
            quantity_actual=quantity_actual,
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            quantity_divergence=quantity_divergence,
            supplier=supplier,
            document_id=document_id,
            origin_document=origin_document,
            operator_id=operator_id,
            metadata=metadata or {},
        )
    )


def test_repository_bootstrap_creates_operational_audit_events_table(
    tmp_path,
):
    _, db_path = _repository(
        tmp_path
    )

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
            """,
            (
                AUDIT_TABLE,
            ),
        ).fetchone()

    assert row is not None


def test_operational_audit_table_has_structured_documentary_fields(
    tmp_path,
):
    _, db_path = _repository(
        tmp_path
    )

    columns = _table_columns(
        db_path
    )

    expected = {
        "id",
        "event_type",
        "product_id",
        "batch_code",
        "location_id",
        "quantity_planned",
        "quantity_actual",
        "quantity_before",
        "quantity_after",
        "quantity_divergence",
        "supplier",
        "document_id",
        "origin_document",
        "operator_id",
        "occurred_at",
        "metadata_json",
    }

    assert expected.issubset(
        columns.keys()
    )


def test_operational_audit_event_requires_event_product_and_operator(
    tmp_path,
):
    _, db_path = _repository(
        tmp_path
    )

    columns = _table_columns(
        db_path
    )

    assert columns["event_type"][3] == 1
    assert columns["product_id"][3] == 1
    assert columns["operator_id"][3] == 1


def test_repository_exposes_append_only_audit_writer(
    tmp_path,
):
    repository, _ = _repository(
        tmp_path
    )

    assert callable(
        getattr(
            repository,
            "append_operational_audit_event",
            None,
        )
    )


def test_append_operational_audit_event_persists_structured_data(
    tmp_path,
):
    repository, db_path = _repository(
        tmp_path
    )

    product = _insert_product(
        repository
    )

    event_id = _append_event(
        repository,
        product_id=product.id,
        event_type="RECEBIMENTO",
        batch_code="LOT-001",
        location_id="",
        quantity_actual=12,
        quantity_before=0,
        quantity_after=12,
        supplier="DISTRIBUIDORA TESTE",
        document_id="NF-001",
        origin_document="MANUAL",
        operator_id="OP-001",
        metadata={
            "traceability": "TEST",
        },
    )

    assert event_id is not None

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            f"""
            SELECT *
            FROM {AUDIT_TABLE}
            WHERE id = ?
            """,
            (
                event_id,
            ),
        ).fetchone()

    assert row is not None

    data = dict(
        row
    )

    assert data["event_type"] == "RECEBIMENTO"
    assert data["product_id"] == product.id
    assert data["batch_code"] == "LOT-001"
    assert data["quantity_actual"] == 12
    assert data["quantity_before"] == 0
    assert data["quantity_after"] == 12
    assert data["supplier"] == "DISTRIBUIDORA TESTE"
    assert data["document_id"] == "NF-001"
    assert data["origin_document"] == "MANUAL"
    assert data["operator_id"] == "OP-001"

    assert json.loads(
        data["metadata_json"]
    ) == {
        "traceability": "TEST",
    }


def test_append_operational_audit_event_does_not_mutate_stock(
    tmp_path,
):
    repository, _ = _repository(
        tmp_path
    )

    product = _insert_product(
        repository
    )

    before = repository.get_by_id(
        product.id
    )

    assert before.quantity == 0
    assert before.batches == {}

    _append_event(
        repository,
        product_id=product.id,
        event_type="AJUSTE_DOCUMENTAL_TESTE",
        quantity_actual=999,
        quantity_before=0,
        quantity_after=999,
    )

    after = repository.get_by_id(
        product.id
    )

    assert after.quantity == 0
    assert after.batches == {}


def test_repository_exposes_product_specific_audit_reader(
    tmp_path,
):
    repository, _ = _repository(
        tmp_path
    )

    assert callable(
        getattr(
            repository,
            "get_operational_audit_events_by_product",
            None,
        )
    )


def test_product_specific_reader_does_not_mix_products(
    tmp_path,
):
    repository, _ = _repository(
        tmp_path
    )

    first = _insert_product(
        repository,
        name="PRIMEIRO PRODUTO AUDITORIA",
        ean="7890000000001",
    )

    second = _insert_product(
        repository,
        name="SEGUNDO PRODUTO AUDITORIA",
        ean="7890000000002",
    )

    _append_event(
        repository,
        product_id=first.id,
        event_type="RECEBIMENTO",
        quantity_actual=10,
        quantity_before=0,
        quantity_after=10,
    )

    _append_event(
        repository,
        product_id=second.id,
        event_type="RECEBIMENTO",
        quantity_actual=20,
        quantity_before=0,
        quantity_after=20,
    )

    events = (
        repository
        .get_operational_audit_events_by_product(
            first.id
        )
    )

    assert len(events) == 1
    assert events[0]["product_id"] == first.id
    assert events[0]["quantity_actual"] == 10


def test_product_specific_reader_preserves_append_order(
    tmp_path,
):
    repository, _ = _repository(
        tmp_path
    )

    product = _insert_product(
        repository
    )

    first_id = _append_event(
        repository,
        product_id=product.id,
        event_type="RECEBIMENTO",
        quantity_actual=12,
        quantity_before=0,
        quantity_after=12,
    )

    second_id = _append_event(
        repository,
        product_id=product.id,
        event_type="PUTAWAY",
        quantity_actual=0,
        quantity_before=12,
        quantity_after=12,
        location_id="BOX-A1",
    )

    events = (
        repository
        .get_operational_audit_events_by_product(
            product.id
        )
    )

    assert [
        event["id"]
        for event in events
    ] == [
        first_id,
        second_id,
    ]


def test_replenishment_audit_can_represent_partial_divergence(
    tmp_path,
):
    repository, _ = _repository(
        tmp_path
    )

    product = _insert_product(
        repository
    )

    _append_event(
        repository,
        product_id=product.id,
        event_type="ABASTECIMENTO_LOJA",
        batch_code="LOT-001",
        location_id="BOX-A1",
        quantity_planned=4,
        quantity_actual=3,
        quantity_before=12,
        quantity_after=9,
        quantity_divergence=1,
        operator_id="OP-001",
    )

    events = (
        repository
        .get_operational_audit_events_by_product(
            product.id
        )
    )

    event = events[0]

    assert event["quantity_planned"] == 4
    assert event["quantity_actual"] == 3
    assert event["quantity_divergence"] == 1
    assert event["quantity_before"] == 12
    assert event["quantity_after"] == 9
    assert event["batch_code"] == "LOT-001"
    assert event["location_id"] == "BOX-A1"


def test_audit_event_timestamp_is_persisted_by_database(
    tmp_path,
):
    repository, db_path = _repository(
        tmp_path
    )

    product = _insert_product(
        repository
    )

    event_id = _append_event(
        repository,
        product_id=product.id,
    )

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            f"""
            SELECT occurred_at
            FROM {AUDIT_TABLE}
            WHERE id = ?
            """,
            (
                event_id,
            ),
        ).fetchone()

    assert row is not None
    assert row[0]


def test_audit_events_are_append_only_in_storage_contract(
    tmp_path,
):
    repository, db_path = _repository(
        tmp_path
    )

    product = _insert_product(
        repository
    )

    first_id = _append_event(
        repository,
        product_id=product.id,
        event_type="RECEBIMENTO",
        quantity_actual=10,
        quantity_before=0,
        quantity_after=10,
    )

    second_id = _append_event(
        repository,
        product_id=product.id,
        event_type="PUTAWAY",
        quantity_actual=0,
        quantity_before=10,
        quantity_after=10,
        location_id="BOX-A1",
    )

    assert first_id != second_id

    with sqlite3.connect(db_path) as conn:
        count = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM {AUDIT_TABLE}
            WHERE product_id = ?
            """,
            (
                product.id,
            ),
        ).fetchone()[0]

    assert count == 2
