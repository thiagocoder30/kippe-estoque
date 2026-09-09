from datetime import datetime, timezone

import pytest

import app as app_module


PRODUCT_ID = "SKU-AUDIT-HISTORY-002B"


@pytest.fixture(autouse=True)
def _isolated_testing_environment(monkeypatch):
    monkeypatch.setattr(
        app_module.container.config,
        "ENV",
        "testing",
    )


def _event(
    event_id,
    event_type,
    occurred_at,
    *,
    batch_code="LOT-HISTORY",
    location_id=None,
    quantity_actual=None,
    quantity_before=None,
    quantity_after=None,
    supplier=None,
    document_id=None,
    origin_document=None,
    operator_id="1001",
    metadata_json="{}",
):
    return {
        "id": event_id,
        "event_type": event_type,
        "product_id": PRODUCT_ID,
        "batch_code": batch_code,
        "location_id": location_id,
        "quantity_planned": None,
        "quantity_actual": quantity_actual,
        "quantity_before": quantity_before,
        "quantity_after": quantity_after,
        "quantity_divergence": None,
        "supplier": supplier,
        "document_id": document_id,
        "origin_document": origin_document,
        "operator_id": operator_id,
        "occurred_at": occurred_at,
        "metadata_json": metadata_json,
    }


def _history_events():
    return [
        _event(
            10,
            "RECEBIMENTO",
            "2026-09-08T12:00:00+00:00",
            quantity_actual=40,
            quantity_before=0,
            quantity_after=40,
            supplier="FORNECEDOR ANTIGO",
            document_id="NF-100",
            origin_document="NOTA FISCAL",
        ),
        _event(
            11,
            "PUTAWAY",
            "2026-09-08T12:10:00+00:00",
            location_id="BOX-A1",
            quantity_before=40,
            quantity_after=40,
        ),
        _event(
            12,
            "RECEBIMENTO",
            "2026-09-09T15:00:00+00:00",
            batch_code="LOT-NEW",
            quantity_actual=60,
            quantity_before=40,
            quantity_after=100,
            supplier="FORNECEDOR NOVO",
            document_id="NF-200",
            origin_document="NOTA FISCAL",
        ),
        _event(
            13,
            "PUTAWAY",
            "2026-09-09T15:05:00+00:00",
            batch_code="LOT-NEW",
            location_id="BOX-E2",
            quantity_before=100,
            quantity_after=100,
        ),
        _event(
            14,
            "ABASTECIMENTO_LOJA",
            "2026-09-09T16:00:00+00:00",
            batch_code="LOT-HISTORY",
            location_id="BOX-A1",
            quantity_actual=5,
            quantity_before=100,
            quantity_after=95,
        ),
    ]


def _client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def _login_override_headers():
    return {
        "X-Test-Operator-Override": "1001",
    }


def test_product_history_endpoint_requires_authentication():
    client = _client()

    response = client.get(
        f"/api/products/{PRODUCT_ID}/history"
    )

    assert response.status_code == 401


def test_product_history_endpoint_returns_404_for_unknown_product(
    monkeypatch,
):
    repository = app_module.container.repository

    monkeypatch.setattr(
        repository,
        "get_by_id",
        lambda product_id: None,
    )

    client = _client()

    response = client.get(
        f"/api/products/{PRODUCT_ID}/history",
        headers=_login_override_headers(),
    )

    assert response.status_code == 404

    payload = response.get_json()

    assert payload
    assert payload.get("success") is False


def test_product_history_endpoint_returns_chronological_events(
    monkeypatch,
):
    repository = app_module.container.repository

    product = object()

    monkeypatch.setattr(
        repository,
        "get_by_id",
        lambda product_id: (
            product
            if product_id == PRODUCT_ID
            else None
        ),
    )

    monkeypatch.setattr(
        repository,
        "get_operational_audit_events_by_product",
        lambda product_id: list(
            reversed(_history_events())
        ),
    )

    client = _client()

    response = client.get(
        f"/api/products/{PRODUCT_ID}/history",
        headers=_login_override_headers(),
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert payload["success"] is True
    assert payload["product_id"] == PRODUCT_ID

    events = payload["events"]

    assert [
        event["id"]
        for event in events
    ] == [
        10,
        11,
        12,
        13,
        14,
    ]


def test_product_history_latest_receiving_ignores_later_non_receiving_events(
    monkeypatch,
):
    repository = app_module.container.repository

    monkeypatch.setattr(
        repository,
        "get_by_id",
        lambda product_id: object(),
    )

    monkeypatch.setattr(
        repository,
        "get_operational_audit_events_by_product",
        lambda product_id: _history_events(),
    )

    client = _client()

    response = client.get(
        f"/api/products/{PRODUCT_ID}/history",
        headers=_login_override_headers(),
    )

    assert response.status_code == 200

    payload = response.get_json()

    latest = payload["latest_receiving"]

    assert latest["id"] == 12
    assert latest["event_type"] == "RECEBIMENTO"
    assert latest["supplier"] == "FORNECEDOR NOVO"
    assert latest["document_id"] == "NF-200"
    assert latest["batch_code"] == "LOT-NEW"
    assert latest["quantity_actual"] == 60
    assert latest["operator_id"] == "1001"


def test_product_history_without_receiving_returns_null_latest_receiving(
    monkeypatch,
):
    repository = app_module.container.repository

    events = [
        _event(
            21,
            "PUTAWAY",
            "2026-09-09T15:05:00+00:00",
            location_id="BOX-E2",
        ),
        _event(
            22,
            "ABASTECIMENTO_LOJA",
            "2026-09-09T16:00:00+00:00",
            location_id="BOX-E2",
            quantity_actual=3,
        ),
    ]

    monkeypatch.setattr(
        repository,
        "get_by_id",
        lambda product_id: object(),
    )

    monkeypatch.setattr(
        repository,
        "get_operational_audit_events_by_product",
        lambda product_id: events,
    )

    client = _client()

    response = client.get(
        f"/api/products/{PRODUCT_ID}/history",
        headers=_login_override_headers(),
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert payload["latest_receiving"] is None
    assert len(payload["events"]) == 2


def test_product_history_empty_documentary_history_is_valid(
    monkeypatch,
):
    repository = app_module.container.repository

    monkeypatch.setattr(
        repository,
        "get_by_id",
        lambda product_id: object(),
    )

    monkeypatch.setattr(
        repository,
        "get_operational_audit_events_by_product",
        lambda product_id: [],
    )

    client = _client()

    response = client.get(
        f"/api/products/{PRODUCT_ID}/history",
        headers=_login_override_headers(),
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert payload["success"] is True
    assert payload["product_id"] == PRODUCT_ID
    assert payload["latest_receiving"] is None
    assert payload["events"] == []


def test_product_history_does_not_expose_documentary_balance_fields(
    monkeypatch,
):
    repository = app_module.container.repository

    monkeypatch.setattr(
        repository,
        "get_by_id",
        lambda product_id: object(),
    )

    monkeypatch.setattr(
        repository,
        "get_operational_audit_events_by_product",
        lambda product_id: _history_events(),
    )

    client = _client()

    response = client.get(
        f"/api/products/{PRODUCT_ID}/history",
        headers=_login_override_headers(),
    )

    assert response.status_code == 200

    payload = response.get_json()

    forbidden_top_level = {
        "balance",
        "saldo",
        "stock",
        "quantity",
        "store_balance",
        "store_quantity",
    }

    assert (
        forbidden_top_level
        .intersection(payload.keys())
        == set()
    )

    # quantity_before/after pertencem ao documento histórico
    # de cada evento e NÃO representam um saldo derivado da
    # tabela de auditoria.
    assert payload["events"][0]["quantity_before"] == 0
    assert payload["events"][0]["quantity_after"] == 40


def test_product_history_preserves_documentary_fields(
    monkeypatch,
):
    repository = app_module.container.repository

    monkeypatch.setattr(
        repository,
        "get_by_id",
        lambda product_id: object(),
    )

    monkeypatch.setattr(
        repository,
        "get_operational_audit_events_by_product",
        lambda product_id: _history_events(),
    )

    client = _client()

    response = client.get(
        f"/api/products/{PRODUCT_ID}/history",
        headers=_login_override_headers(),
    )

    assert response.status_code == 200

    payload = response.get_json()

    receiving = payload["events"][0]

    assert receiving["event_type"] == "RECEBIMENTO"
    assert receiving["supplier"] == "FORNECEDOR ANTIGO"
    assert receiving["document_id"] == "NF-100"
    assert receiving["origin_document"] == "NOTA FISCAL"
    assert receiving["batch_code"] == "LOT-HISTORY"
    assert receiving["quantity_actual"] == 40
    assert receiving["operator_id"] == "1001"
    assert receiving["occurred_at"] == (
        "2026-09-08T12:00:00+00:00"
    )


def test_product_history_endpoint_is_get_only(
    monkeypatch,
):
    repository = app_module.container.repository

    monkeypatch.setattr(
        repository,
        "get_by_id",
        lambda product_id: object(),
    )

    client = _client()

    response = client.post(
        f"/api/products/{PRODUCT_ID}/history",
        json={},
        headers=_login_override_headers(),
    )

    assert response.status_code == 405
