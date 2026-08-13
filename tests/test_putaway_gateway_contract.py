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

    container.product_repository._init_db()

    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client

    if os.path.exists(test_config.DB_PATH):
        os.remove(test_config.DB_PATH)

    if os.path.exists(test_config.LOG_PATH):
        os.remove(test_config.LOG_PATH)


def test_putaway_gateway_contract(client):
    headers = {
        "X-Test-Operator-Override": "SYSTEM-TEST-AGENT",
        "X-Test-Role-Override": "GERENTE",
    }

    create = client.post(
        "/api/produto",
        json={
            "id": "TEST-PUTAWAY",
            "name": "Produto Teste Putaway",
        },
        headers=headers,
    )

    assert create.status_code == 201

    receive = client.post(
        "/api/entrada",
        json={
            "id": "TEST-PUTAWAY",
            "amount": 10,
            "expiration_date": "2035-12-31",
            "batch_code": "B001",
        },
        headers=headers,
    )

    assert receive.status_code == 200

    response = client.post(
        "/api/putaway",
        json={
            "sku": "TEST-PUTAWAY",
            "batch_code": "B001",
            "location_id": "EST-A-01",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json["message"] == "Putaway registrado."

    product = client.get("/api/produto/TEST-PUTAWAY")

    assert product.status_code == 200
