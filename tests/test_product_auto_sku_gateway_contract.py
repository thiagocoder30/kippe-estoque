import os

import pytest

from src.infrastructure.config import Config


@pytest.fixture
def product_gateway():
    from app import app, container

    test_config = Config.for_testing()
    container.config = test_config

    container._logger = None
    container._product_repository = None
    container._operator_repository = None
    container._manage_stock_use_case = None
    container._receiving_use_case = None
    container._product_query_use_case = None
    container._product_suggestion_use_case = None
    container._identity_provider = None

    container.product_repository._init_db()

    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client, container

    if os.path.exists(test_config.DB_PATH):
        os.remove(test_config.DB_PATH)

    if os.path.exists(test_config.LOG_PATH):
        os.remove(test_config.LOG_PATH)


def headers_for(role):
    return {
        "X-Test-Operator-Override": "PRODUCT-GATEWAY-TEST",
        "X-Test-Role-Override": role,
    }


def test_manager_can_register_product_without_supplying_sku(
    product_gateway,
):
    client, container = product_gateway

    response = client.post(
        "/api/produto",
        json={
            "name": "Arroz Branco 5kg",
            "ean": "7890000001015",
            "unit_of_measure": "un",
            "category_id": None,
        },
        headers=headers_for("GERENTE"),
    )

    assert response.status_code == 201
    assert response.is_json

    data = response.get_json()

    assert data["message"] == "Produto cadastrado."

    product = data["product"]

    assert product["id"] == "SKU000001"
    assert product["name"] == "Arroz Branco 5kg"
    assert product["ean"] == "7890000001015"
    assert product["unit_of_measure"] == "un"
    assert product["category_id"] is None

    persisted = container.product_repository.get_by_id(
        "SKU000001"
    )

    assert persisted is not None
    assert persisted.ean == "7890000001015"


def test_admin_sistema_can_register_product_without_sku(
    product_gateway,
):
    client, _ = product_gateway

    response = client.post(
        "/api/produto",
        json={
            "name": "Feijão Carioca 1kg",
            "ean": "7890000001022",
            "unit_of_measure": "un",
        },
        headers=headers_for("ADMIN_SISTEMA"),
    )

    assert response.status_code == 201

    product = response.get_json()["product"]

    assert product["id"] == "SKU000001"
    assert product["ean"] == "7890000001022"


def test_operator_cannot_register_product(
    product_gateway,
):
    client, container = product_gateway

    response = client.post(
        "/api/produto",
        json={
            "name": "Produto Não Autorizado",
            "ean": "7890000001039",
            "unit_of_measure": "un",
        },
        headers=headers_for("OPERADOR"),
    )

    assert response.status_code == 403
    assert response.is_json
    assert "Autorização negada" in response.get_json()["error"]

    assert container.product_repository.get_by_ean(
        "7890000001039"
    ) is None


def test_unauthenticated_registration_returns_401(
    product_gateway,
):
    client, _ = product_gateway

    response = client.post(
        "/api/produto",
        json={
            "name": "Produto Sem Sessão",
            "ean": "7890000001046",
            "unit_of_measure": "un",
        },
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == (
        "Operador não autenticado."
    )


def test_duplicate_ean_returns_conflict(
    product_gateway,
):
    client, container = product_gateway

    first = client.post(
        "/api/produto",
        json={
            "name": "Produto Original",
            "ean": "7890000001053",
            "unit_of_measure": "un",
        },
        headers=headers_for("GERENTE"),
    )

    duplicate = client.post(
        "/api/produto",
        json={
            "name": "Produto Duplicado",
            "ean": "7890000001053",
            "unit_of_measure": "un",
        },
        headers=headers_for("GERENTE"),
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409

    data = duplicate.get_json()

    assert "EAN" in data["error"]
    assert "já" in data["error"].lower()

    products = container.product_repository.get_all()

    matching = [
        product
        for product in products
        if product.ean == "7890000001053"
    ]

    assert len(matching) == 1


def test_generated_product_can_be_queried_by_ean(
    product_gateway,
):
    client, _ = product_gateway

    creation = client.post(
        "/api/produto",
        json={
            "name": "Leite Integral 1L",
            "ean": "7890000001060",
            "unit_of_measure": "un",
        },
        headers=headers_for("GERENTE"),
    )

    assert creation.status_code == 201

    generated_sku = creation.get_json()["product"]["id"]

    query = client.get(
        "/api/product/query",
        query_string={
            "identifier": "7890000001060"
        },
    )

    assert query.status_code == 200

    data = query.get_json()

    assert data["id"] == generated_sku
    assert data["ean"] == "7890000001060"
    assert data["name"] == "Leite Integral 1L"


def test_legacy_explicit_sku_contract_remains_temporarily_supported(
    product_gateway,
):
    client, container = product_gateway

    response = client.post(
        "/api/produto",
        json={
            "id": "LEGACY-GATEWAY-001",
            "name": "Produto Legado",
            "ean": "7890000001077",
            "unit_of_measure": "un",
        },
        headers=headers_for("GERENTE"),
    )

    assert response.status_code == 201

    persisted = container.product_repository.get_by_id(
        "LEGACY-GATEWAY-001"
    )

    assert persisted is not None
    assert persisted.name == "Produto Legado"
