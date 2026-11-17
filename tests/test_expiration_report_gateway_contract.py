import os

import pytest

from src.infrastructure.config import Config


@pytest.fixture
def client():
    from app import app, container

    test_config = Config.for_testing()

    previous_config = container.config
    previous_testing = app.config.get("TESTING")

    cache_names = (
        "_logger",
        "_product_repository",
        "_operator_repository",
        "_manage_stock_use_case",
        "_product_query_use_case",
        "_product_suggestion_use_case",
    )

    previous_cache = {
        name: getattr(container, name)
        for name in cache_names
    }

    container.config = test_config

    for name in cache_names:
        setattr(container, name, None)

    container.product_repository._init_db()

    app.config["TESTING"] = True

    try:
        with app.test_client() as test_client:
            yield test_client
    finally:
        container.config = previous_config

        for name, value in previous_cache.items():
            setattr(container, name, value)

        if previous_testing is None:
            app.config.pop("TESTING", None)
        else:
            app.config["TESTING"] = previous_testing

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

    # Nova API retorna {items, summary, generated_at}
    assert isinstance(data, dict)
    assert "items" in data
    assert "summary" in data
    assert len(data["items"]) == 1

    item = data["items"][0]

    assert item["sku"] == "SKU-REPORT-001"
    assert item["name"] == "Produto Relatório"
    assert item["batch"] == "L-REPORT-001"
    assert item["expiration"] == "2035-12-31"
    assert item["status"] == "NORMAL"
