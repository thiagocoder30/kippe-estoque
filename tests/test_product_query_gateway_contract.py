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


def test_product_query_gateway_returns_operational_view(client):
    headers = {
        "X-Test-Operator-Override": "SYSTEM-TEST-AGENT",
        "X-Test-Role-Override": "GERENTE",
    }

    create = client.post(
        "/api/produto",
        json={
            "id": "SKU-QUERY-001",
            "name": "Leite Integral 1L",
        },
        headers=headers,
    )

    assert create.status_code == 201

    receive = client.post(
        "/api/entrada",
        json={
            "id": "SKU-QUERY-001",
            "amount": 20,
            "expiration_date": "2035-12-31",
            "batch_code": "L001",
        },
        headers=headers,
    )

    assert receive.status_code == 200

    response = client.get(
        "/api/product/query",
        query_string={
            "identifier": "SKU-QUERY-001"
        },
    )

    assert response.status_code == 200
    assert response.is_json

    data = response.json

    assert data["id"] == "SKU-QUERY-001"
    assert data["name"] == "Leite Integral 1L"
    assert data["quantity"] == 20

    assert len(data["batches"]) == 1

    batch = data["batches"][0]

    assert batch["code"] == "L001"
    assert batch["expiration_date"] == "2035-12-31"
    assert batch["expiration_status"] == "NORMAL"
    assert batch["days_remaining"] > 0


def test_product_query_gateway_requires_identifier(client):

    response = client.get(
        "/api/product/query"
    )

    assert response.status_code == 400
    assert response.is_json
    assert response.json["error"] == "Identificador obrigatório."


def test_product_query_gateway_returns_not_found_for_unknown_product(client):

    response = client.get(
        "/api/product/query",
        query_string={
            "identifier": "SKU-INEXISTENTE"
        },
    )

    assert response.status_code == 404
    assert response.is_json
    assert response.json["error"] == "PRODUTO_NAO_CADASTRADO"
