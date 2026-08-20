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


def test_expiration_report_returns_real_inventory_batches(client):

    headers = {
        "X-Test-Operator-Override": "SYSTEM-TEST-AGENT",
        "X-Test-Role-Override": "GERENTE",
    }

    create = client.post(
        "/api/produto",
        json={
            "id": "SKU-REPORT-001",
            "name": "Produto Relatório",
            "ean": "7897777777777",
        },
        headers=headers,
    )

    assert create.status_code == 201

    receive = client.post(
        "/api/receive",
        json={
            "sku": "SKU-REPORT-001",
            "quantity": 10,
            "batch_code": "L-REPORT-001",
            "expiration_date": "2035-12-31",
            "supplier": "FORNECEDOR TESTE",
        },
        headers=headers,
    )

    assert receive.status_code == 200

    response = client.get(
        "/api/relatorios/vencimentos"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) == 1

    item = data[0]

    assert item["sku"] == "SKU-REPORT-001"
    assert item["name"] == "Produto Relatório"
    assert item["batch"] == "L-REPORT-001"
    assert item["expiration"] == "2035-12-31"
    assert item["status"] == "NORMAL"
