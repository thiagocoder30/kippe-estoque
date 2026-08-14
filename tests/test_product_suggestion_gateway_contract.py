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

    if hasattr(container, "_product_suggestion_use_case"):
        container._product_suggestion_use_case = None

    container.product_repository._init_db()

    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client

    if os.path.exists(test_config.DB_PATH):
        os.remove(test_config.DB_PATH)

    if os.path.exists(test_config.LOG_PATH):
        os.remove(test_config.LOG_PATH)


def test_product_suggestion_gateway_returns_matching_products(client):
    headers = {
        "X-Test-Operator-Override": "SYSTEM-TEST-AGENT",
        "X-Test-Role-Override": "GERENTE",
    }

    products = [
        {
            "id": "SKU-SUG-001",
            "name": "Leite Integral 1L",
        },
        {
            "id": "SKU-SUG-002",
            "name": "Leite Zero Lactose 1L",
        },
        {
            "id": "SKU-SUG-003",
            "name": "Arroz Branco 5kg",
        },
    ]

    for product in products:
        response = client.post(
            "/api/produto",
            json=product,
            headers=headers,
        )

        assert response.status_code == 201

    response = client.get(
        "/api/product/suggestions",
        query_string={
            "q": "leite"
        },
    )

    assert response.status_code == 200
    assert response.is_json

    data = response.json

    assert len(data) == 2

    assert data[0]["id"] == "SKU-SUG-001"
    assert data[0]["name"] == "Leite Integral 1L"

    assert data[1]["id"] == "SKU-SUG-002"
    assert data[1]["name"] == "Leite Zero Lactose 1L"

    assert "quantity" not in data[0]
    assert "batches" not in data[0]


def test_product_suggestion_gateway_returns_empty_for_blank_query(client):

    response = client.get(
        "/api/product/suggestions",
        query_string={
            "q": "   "
        },
    )

    assert response.status_code == 200
    assert response.is_json
    assert response.json == []
