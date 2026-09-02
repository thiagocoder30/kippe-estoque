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


def create_product(client, sku, name="Produto Abastecimento"):
    response = client.post(
        "/api/produto",
        json={
            "id": sku,
            "name": name,
        },
        headers=auth_headers(),
    )

    assert response.status_code == 201


def receive_batch(
    client,
    *,
    sku,
    batch,
    quantity,
    expiration,
):
    response = client.post(
        "/api/entrada",
        json={
            "id": sku,
            "amount": quantity,
            "expiration_date": expiration,
            "batch_code": batch,
        },
        headers=auth_headers(),
    )

    assert response.status_code == 200


def query_product(client, sku):
    response = client.get(
        "/api/product/query",
        query_string={
            "identifier": sku,
        },
    )

    assert response.status_code == 200
    return response.json


def get_batch(product, code):
    matches = [
        batch
        for batch in product["batches"]
        if batch["code"] == code
    ]

    assert len(matches) == 1
    return matches[0]


def request_plan(client, items, *, authenticated=True):
    headers = auth_headers() if authenticated else {}

    return client.post(
        "/api/abastecimento/plano",
        json={
            "items": items,
        },
        headers=headers,
    )


def test_replenishment_plan_requires_authentication(client):
    create_product(
        client,
        "SKU-CART-AUTH-001",
    )

    receive_batch(
        client,
        sku="SKU-CART-AUTH-001",
        batch="LOT-AUTH-001",
        quantity=10,
        expiration="2030-01-01",
    )

    response = request_plan(
        client,
        [
            {
                "sku": "SKU-CART-AUTH-001",
                "quantity": 2,
            }
        ],
        authenticated=False,
    )

    assert response.status_code == 401
    assert response.is_json

    assert (
        response.json["error"]
        == "Operador não autenticado."
    )


def test_replenishment_plan_uses_earliest_expiring_batch_first(
    client,
):
    sku = "SKU-CART-FEFO-001"

    create_product(
        client,
        sku,
        name="Leite Integral 1L",
    )

    receive_batch(
        client,
        sku=sku,
        batch="LOT-LONGE",
        quantity=10,
        expiration="2030-12-31",
    )

    receive_batch(
        client,
        sku=sku,
        batch="LOT-PERTO",
        quantity=5,
        expiration="2029-01-01",
    )

    response = request_plan(
        client,
        [
            {
                "sku": sku,
                "quantity": 3,
            }
        ],
    )

    assert response.status_code == 200
    assert response.is_json

    payload = response.json

    assert len(payload["items"]) == 1

    item = payload["items"][0]

    assert item["sku"] == sku
    assert item["name"] == "Leite Integral 1L"
    assert item["requested_quantity"] == 3

    assert len(item["allocations"]) == 1

    allocation = item["allocations"][0]

    assert allocation["batch_code"] == "LOT-PERTO"
    assert allocation["expiration_date"] == "2029-01-01"
    assert allocation["quantity"] == 3


def test_replenishment_plan_splits_requested_quantity_across_fefo_batches(
    client,
):
    sku = "SKU-CART-FEFO-002"

    create_product(
        client,
        sku,
        name="Cafe Tradicional 500G",
    )

    receive_batch(
        client,
        sku=sku,
        batch="LOT-PRIMEIRO",
        quantity=4,
        expiration="2029-02-01",
    )

    receive_batch(
        client,
        sku=sku,
        batch="LOT-SEGUNDO",
        quantity=10,
        expiration="2030-02-01",
    )

    response = request_plan(
        client,
        [
            {
                "sku": sku,
                "quantity": 7,
            }
        ],
    )

    assert response.status_code == 200

    item = response.json["items"][0]

    assert item["requested_quantity"] == 7
    assert len(item["allocations"]) == 2

    first = item["allocations"][0]
    second = item["allocations"][1]

    assert first["batch_code"] == "LOT-PRIMEIRO"
    assert first["expiration_date"] == "2029-02-01"
    assert first["quantity"] == 4

    assert second["batch_code"] == "LOT-SEGUNDO"
    assert second["expiration_date"] == "2030-02-01"
    assert second["quantity"] == 3


def test_replenishment_plan_does_not_mutate_stock(client):
    sku = "SKU-CART-NOMUT-001"

    create_product(client, sku)

    receive_batch(
        client,
        sku=sku,
        batch="LOT-NOMUT-001",
        quantity=8,
        expiration="2030-05-01",
    )

    before = query_product(client, sku)

    response = request_plan(
        client,
        [
            {
                "sku": sku,
                "quantity": 5,
            }
        ],
    )

    assert response.status_code == 200

    after = query_product(client, sku)

    assert before["quantity"] == 8
    assert after["quantity"] == 8

    assert (
        get_batch(
            before,
            "LOT-NOMUT-001",
        )["quantity"]
        == 8
    )

    assert (
        get_batch(
            after,
            "LOT-NOMUT-001",
        )["quantity"]
        == 8
    )


def test_replenishment_plan_supports_multiple_cart_products(
    client,
):
    create_product(
        client,
        "SKU-CART-MULTI-001",
        name="Produto A",
    )

    create_product(
        client,
        "SKU-CART-MULTI-002",
        name="Produto B",
    )

    receive_batch(
        client,
        sku="SKU-CART-MULTI-001",
        batch="LOT-A-001",
        quantity=10,
        expiration="2030-06-01",
    )

    receive_batch(
        client,
        sku="SKU-CART-MULTI-002",
        batch="LOT-B-001",
        quantity=20,
        expiration="2030-07-01",
    )

    response = request_plan(
        client,
        [
            {
                "sku": "SKU-CART-MULTI-001",
                "quantity": 3,
            },
            {
                "sku": "SKU-CART-MULTI-002",
                "quantity": 7,
            },
        ],
    )

    assert response.status_code == 200

    payload = response.json

    assert len(payload["items"]) == 2

    by_sku = {
        item["sku"]: item
        for item in payload["items"]
    }

    assert (
        by_sku["SKU-CART-MULTI-001"]
        ["requested_quantity"]
        == 3
    )

    assert (
        by_sku["SKU-CART-MULTI-002"]
        ["requested_quantity"]
        == 7
    )


def test_replenishment_plan_rejects_insufficient_stock_without_mutation(
    client,
):
    sku = "SKU-CART-STOCK-001"

    create_product(client, sku)

    receive_batch(
        client,
        sku=sku,
        batch="LOT-STOCK-001",
        quantity=5,
        expiration="2030-08-01",
    )

    before = query_product(client, sku)

    response = request_plan(
        client,
        [
            {
                "sku": sku,
                "quantity": 8,
            }
        ],
    )

    assert response.status_code == 400
    assert response.is_json

    after = query_product(client, sku)

    assert before["quantity"] == 5
    assert after["quantity"] == 5

    assert (
        get_batch(
            after,
            "LOT-STOCK-001",
        )["quantity"]
        == 5
    )


@pytest.mark.parametrize(
    "quantity",
    [
        0,
        -1,
    ],
)
def test_replenishment_plan_rejects_non_positive_quantity(
    client,
    quantity,
):
    sku = f"SKU-CART-QTY-{abs(quantity)}"

    create_product(client, sku)

    receive_batch(
        client,
        sku=sku,
        batch=f"LOT-QTY-{abs(quantity)}",
        quantity=5,
        expiration="2030-09-01",
    )

    response = request_plan(
        client,
        [
            {
                "sku": sku,
                "quantity": quantity,
            }
        ],
    )

    assert response.status_code == 400

    product = query_product(client, sku)

    assert product["quantity"] == 5


def test_replenishment_plan_rejects_empty_cart(client):
    response = request_plan(
        client,
        [],
    )

    assert response.status_code == 400


def test_replenishment_plan_consolidates_duplicate_sku_before_fefo(
    client,
):
    sku = "SKU-CART-DUP-001"

    create_product(
        client,
        sku,
        name="Produto Duplicado",
    )

    receive_batch(
        client,
        sku=sku,
        batch="LOT-DUP-FIRST",
        quantity=5,
        expiration="2029-10-01",
    )

    receive_batch(
        client,
        sku=sku,
        batch="LOT-DUP-SECOND",
        quantity=10,
        expiration="2030-10-01",
    )

    response = request_plan(
        client,
        [
            {
                "sku": sku,
                "quantity": 3,
            },
            {
                "sku": sku,
                "quantity": 4,
            },
        ],
    )

    assert response.status_code == 200
    assert response.is_json

    payload = response.json

    assert len(payload["items"]) == 1

    item = payload["items"][0]

    assert item["sku"] == sku
    assert item["requested_quantity"] == 7

    assert len(item["allocations"]) == 2

    first = item["allocations"][0]
    second = item["allocations"][1]

    assert first["batch_code"] == "LOT-DUP-FIRST"
    assert first["quantity"] == 5

    assert second["batch_code"] == "LOT-DUP-SECOND"
    assert second["quantity"] == 2


def test_replenishment_plan_checks_combined_duplicate_quantity_atomically(
    client,
):
    sku = "SKU-CART-DUP-STOCK-001"

    create_product(client, sku)

    receive_batch(
        client,
        sku=sku,
        batch="LOT-DUP-STOCK-001",
        quantity=5,
        expiration="2030-11-01",
    )

    before = query_product(client, sku)

    response = request_plan(
        client,
        [
            {
                "sku": sku,
                "quantity": 4,
            },
            {
                "sku": sku,
                "quantity": 4,
            },
        ],
    )

    assert response.status_code == 400
    assert response.is_json

    after = query_product(client, sku)

    assert before["quantity"] == 5
    assert after["quantity"] == 5

    assert (
        get_batch(
            after,
            "LOT-DUP-STOCK-001",
        )["quantity"]
        == 5
    )
