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
    container._product_query_use_case = None
    container._product_suggestion_use_case = None

    container.product_repository._init_db()

    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client

    if os.path.exists(test_config.DB_PATH):
        os.remove(test_config.DB_PATH)

    if os.path.exists(test_config.LOG_PATH):
        os.remove(test_config.LOG_PATH)


def test_product_created_via_api_can_be_queried_by_ean(client):

    headers = {
        "X-Test-Operator-Override": "SYSTEM-TEST-AGENT",
        "X-Test-Role-Override": "GERENTE",
    }

    create = client.post(
        "/api/produto",
        json={
            "id": "SKU-EAN-API-001",
            "name": "Leite Integral 1L",
            "ean": "7891234567890",
        },
        headers=headers,
    )

    assert create.status_code == 201

    query = client.get(
        "/api/product/query",
        query_string={
            "identifier": "7891234567890"
        },
    )

    assert query.status_code == 200
    assert query.json["id"] == "SKU-EAN-API-001"
    assert query.json["ean"] == "7891234567890"
    assert query.json["name"] == "Leite Integral 1L"
