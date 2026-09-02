import os

import pytest

from src.infrastructure.config import Config


@pytest.fixture
def client():
    from app import app, container

    test_config = Config.for_testing()
    container.config = test_config

    container._logger = None
    container._product_repository = None
    container._operator_repository = None
    container._manage_stock_use_case = None
    container._receiving_use_case = None
    container._product_query_use_case = None

    container.product_repository._init_db()

    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client

    if os.path.exists(test_config.DB_PATH):
        os.remove(test_config.DB_PATH)

    if os.path.exists(test_config.LOG_PATH):
        os.remove(test_config.LOG_PATH)


def auth_headers():
    return {
        "X-Test-Operator-Override": "SYSTEM-TEST-AGENT",
        "X-Test-Role-Override": "GERENTE",
    }


def create_received_batch(
    client,
    *,
    sku,
    batch,
    quantity,
    expiration,
):
    headers = auth_headers()

    created = client.post(
        "/api/produto",
        json={
            "id": sku,
            "name": "Produto Controle Validade",
        },
        headers=headers,
    )

    assert created.status_code == 201

    received = client.post(
        "/api/entrada",
        json={
            "id": sku,
            "amount": quantity,
            "expiration_date": expiration,
            "batch_code": batch,
        },
        headers=headers,
    )

    assert received.status_code == 200


def test_zero_quantity_batch_remains_in_expiration_report(client):
    create_received_batch(
        client,
        sku="SKU-EXP-TRACK-001",
        batch="LOT-TRACK-001",
        quantity=5,
        expiration="2030-01-10",
    )

    removed = client.post(
        "/api/saida",
        json={
            "id": "SKU-EXP-TRACK-001",
            "amount": 5,
        },
        headers=auth_headers(),
    )

    assert removed.status_code == 200

    response = client.get(
        "/api/relatorios/vencimentos"
    )

    assert response.status_code == 200

    matches = [
        item
        for item in response.json
        if item["sku"] == "SKU-EXP-TRACK-001"
        and item["batch"] == "LOT-TRACK-001"
    ]

    assert len(matches) == 1

    batch = matches[0]

    assert batch["quantity"] == 0
    assert batch["expiration"] == "2030-01-10"


def test_zero_quantity_batch_is_not_fefo_picking_candidate(client):
    create_received_batch(
        client,
        sku="SKU-EXP-TRACK-002",
        batch="LOT-ZERO-FIRST",
        quantity=3,
        expiration="2029-01-01",
    )

    removed = client.post(
        "/api/saida",
        json={
            "id": "SKU-EXP-TRACK-002",
            "amount": 3,
        },
        headers=auth_headers(),
    )

    assert removed.status_code == 200

    received_second = client.post(
        "/api/entrada",
        json={
            "id": "SKU-EXP-TRACK-002",
            "amount": 8,
            "expiration_date": "2030-01-01",
            "batch_code": "LOT-ACTIVE",
        },
        headers=auth_headers(),
    )

    assert received_second.status_code == 200

    response = client.get(
        "/api/reposicao/SKU-EXP-TRACK-002"
    )

    assert response.status_code == 200
    assert response.is_json

    payload = response.json

    assert payload["name"] == "Produto Controle Validade"
    assert payload["total_quantity"] == 8
    assert isinstance(payload["instructions"], list)

    instructions = payload["instructions"]

    zero_batch_mentions = [
        item
        for item in instructions
        if item["lote"] == "LOT-ZERO-FIRST"
    ]

    active_batch_mentions = [
        item
        for item in instructions
        if item["lote"] == "LOT-ACTIVE"
    ]

    assert zero_batch_mentions == []
    assert len(active_batch_mentions) == 1

    assert (
        active_batch_mentions[0]["qtd_disponivel"]
        == 8
    )


def test_zero_quantity_batch_remains_persisted_after_repository_reload(
    client,
):
    from app import container

    create_received_batch(
        client,
        sku="SKU-EXP-TRACK-003",
        batch="LOT-PERSIST-001",
        quantity=4,
        expiration="2031-06-15",
    )

    removed = client.post(
        "/api/saida",
        json={
            "id": "SKU-EXP-TRACK-003",
            "amount": 4,
        },
        headers=auth_headers(),
    )

    assert removed.status_code == 200

    first = (
        container.product_repository
        .get_by_id("SKU-EXP-TRACK-003")
    )

    assert first is not None
    assert (
        first.batches["LOT-PERSIST-001"].quantity
        == 0
    )

    container._product_repository = None

    reloaded = (
        container.product_repository
        .get_by_id("SKU-EXP-TRACK-003")
    )

    assert reloaded is not None
    assert "LOT-PERSIST-001" in reloaded.batches

    assert (
        reloaded
        .batches["LOT-PERSIST-001"]
        .quantity
        == 0
    )


def test_product_total_can_be_zero_while_expiration_remains_trackable(
    client,
):
    create_received_batch(
        client,
        sku="SKU-EXP-TRACK-004",
        batch="LOT-TRACK-004",
        quantity=7,
        expiration="2032-02-20",
    )

    removed = client.post(
        "/api/saida",
        json={
            "id": "SKU-EXP-TRACK-004",
            "amount": 7,
        },
        headers=auth_headers(),
    )

    assert removed.status_code == 200

    product_response = client.get(
        "/api/product/query",
        query_string={
            "identifier": "SKU-EXP-TRACK-004"
        },
    )

    assert product_response.status_code == 200
    assert product_response.json["quantity"] == 0

    expiration_response = client.get(
        "/api/relatorios/vencimentos"
    )

    assert expiration_response.status_code == 200

    tracked = [
        item
        for item in expiration_response.json
        if item["sku"] == "SKU-EXP-TRACK-004"
        and item["batch"] == "LOT-TRACK-004"
    ]

    assert len(tracked) == 1
