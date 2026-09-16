import os

import pytest

from src.infrastructure.config import Config


@pytest.fixture
def client():
    from app import app, container

    original_config = container.config
    original_logger = container._logger
    original_product_repository = container._product_repository
    original_operator_repository = container._operator_repository
    original_manage_stock_use_case = container._manage_stock_use_case
    original_testing = app.config.get("TESTING")

    test_config = Config.for_testing()

    try:
        container.config = test_config

        container._logger = None
        container._product_repository = None
        container._operator_repository = None
        container._manage_stock_use_case = None

        container.product_repository._init_db()

        app.config["TESTING"] = True

        with app.test_client() as test_client:
            yield test_client

    finally:
        container.config = original_config
        container._logger = original_logger
        container._product_repository = original_product_repository
        container._operator_repository = original_operator_repository
        container._manage_stock_use_case = original_manage_stock_use_case

        if original_testing is None:
            app.config.pop("TESTING", None)
        else:
            app.config["TESTING"] = original_testing

        if os.path.exists(test_config.DB_PATH):
            os.remove(test_config.DB_PATH)

        if os.path.exists(test_config.LOG_PATH):
            os.remove(test_config.LOG_PATH)


def test_adjustment_gateway_contract(client):
    headers = {
        "X-Test-Operator-Override": "SYSTEM-TEST-AGENT",
        "X-Test-Role-Override": "GERENTE",
    }

    client.post(
        "/api/produto",
        json={
            "id": "TEST-ADJUSTMENT",
            "name": "Produto Ajuste",
        },
        headers=headers,
    )

    client.post(
        "/api/entrada",
        json={
            "id": "TEST-ADJUSTMENT",
            "amount": 20,
            "expiration_date": "2035-12-31",
            "batch_code": "B001",
        },
        headers=headers,
    )

    response = client.post(
        "/api/adjustment",
        json={
            "sku": "TEST-ADJUSTMENT",
            "quantity": -5,
            "divergence_type": "CONTAGEM",
            "reason": "Auditoria Mobile",
        },
        headers=headers,
    )

    print(response.json)
    assert response.status_code == 200
    assert response.json["message"] == "Ajuste registrado."

    product = client.get("/api/produto/TEST-ADJUSTMENT")

    assert product.status_code == 200
    assert product.json["quantity"] == 15
