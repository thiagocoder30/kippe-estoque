import os

import pytest

from src.infrastructure.config import Config


@pytest.fixture
def receiving_env():
    from app import app, container

    original_config = container.config
    original_testing = app.config.get("TESTING")

    cached_attributes = (
        "_logger",
        "_product_repository",
        "_operator_repository",
        "_manage_stock_use_case",
        "_receiving_use_case",
        "_product_query_use_case",
        "_product_suggestion_use_case",
        "_existing_stock_onboarding_use_case",
    )

    original_cached_state = {
        attribute: getattr(container, attribute, None)
        for attribute in cached_attributes
    }

    test_config = Config.for_testing()

    try:
        container.config = test_config

        for attribute in cached_attributes:
            if hasattr(container, attribute):
                setattr(container, attribute, None)

        container.product_repository._init_db()

        app.config["TESTING"] = True

        with app.test_client() as client:
            yield client, container

    finally:
        container.config = original_config

        for attribute, value in original_cached_state.items():
            if hasattr(container, attribute):
                setattr(container, attribute, value)

        app.config["TESTING"] = original_testing

        if os.path.exists(test_config.DB_PATH):
            os.remove(test_config.DB_PATH)

        if os.path.exists(test_config.LOG_PATH):
            os.remove(test_config.LOG_PATH)


def test_detailed_receiving_preserves_batch_traceability(
    receiving_env,
):
    client, container = receiving_env

    headers = {
        "X-Test-Operator-Override": "SYSTEM-TEST-AGENT",
        "X-Test-Role-Override": "GERENTE",
    }

    create = client.post(
        "/api/produto",
        json={
            "id": "SKU-REC-DETAIL-001",
            "name": "Produto Recebimento Detalhado",
            "ean": "7896098900208",
            "unit_of_measure": "un",
        },
        headers=headers,
    )

    assert create.status_code == 201

    receive = client.post(
        "/api/receive",
        json={
            "sku": "SKU-REC-DETAIL-001",
            "quantity": 24,
            "batch_code": "LOT-20260820",
            "manufacturing_date": "2026-08-01",
            "expiration_date": "2027-02-01",
            "supplier": "DISTRIBUIDORA TESTE",
            "invoice_id": "NF-000123",
            "origin_document": "MANUAL",
        },
        headers=headers,
    )

    assert receive.status_code == 200

    product = container.product_repository.get_by_id(
        "SKU-REC-DETAIL-001"
    )

    assert product is not None

    batch = product.batches["LOT-20260820"]

    assert batch.quantity == 24
    assert batch.manufacturing_date == "2026-08-01"
    assert batch.expiration_date == "2027-02-01"
    assert batch.supplier == "DISTRIBUIDORA TESTE"


def test_detailed_receiving_response_exposes_operational_result(
    receiving_env,
):
    client, _ = receiving_env

    headers = {
        "X-Test-Operator-Override": "SYSTEM-TEST-AGENT",
        "X-Test-Role-Override": "GERENTE",
    }

    create = client.post(
        "/api/produto",
        json={
            "id": "SKU-REC-DETAIL-002",
            "name": "Produto Operacional",
            "ean": "7896098900215",
        },
        headers=headers,
    )

    assert create.status_code == 201

    response = client.post(
        "/api/receive",
        json={
            "sku": "SKU-REC-DETAIL-002",
            "quantity": 10,
            "batch_code": "LOT-DETAIL-002",
            "manufacturing_date": "2026-08-10",
            "expiration_date": "2027-08-10",
            "supplier": "FORNECEDOR TESTE",
            "invoice_id": "NF-002",
            "origin_document": "MANUAL",
        },
        headers=headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["message"] == "Entrada registrada."

    receiving = data["receiving"]

    assert receiving["sku"] == "SKU-REC-DETAIL-002"
    assert receiving["batch_code"] == "LOT-DETAIL-002"
    assert receiving["quantity"] == 10
    assert receiving["supplier"] == "FORNECEDOR TESTE"
    assert receiving["invoice_id"] == "NF-002"
    assert receiving["origin_document"] == "MANUAL"
    assert receiving["putaway_status"] == "PENDENTE"
