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


def create_product(
    client,
    sku,
    name="Produto Coleta",
):
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


def putaway_batch(
    client,
    *,
    sku,
    batch,
    location,
):
    response = client.post(
        "/api/putaway",
        json={
            "sku": sku,
            "batch_code": batch,
            "location_id": location,
        },
        headers=auth_headers(),
    )

    assert response.status_code == 200


def request_pick_plan(
    client,
    items,
    *,
    authenticated=True,
):
    headers = (
        auth_headers()
        if authenticated
        else {}
    )

    return client.post(
        "/api/abastecimento/coleta/plano",
        json={
            "items": items,
        },
        headers=headers,
    )


def query_product(client, sku):
    response = client.get(
        "/api/product/query",
        query_string={
            "identifier": sku,
        },
    )

    assert response.status_code == 200
    return response.json


def get_batch(product, batch_code):
    matches = [
        batch
        for batch in product["batches"]
        if batch["code"] == batch_code
    ]

    assert len(matches) == 1
    return matches[0]


def test_pick_plan_requires_authentication(client):
    response = request_pick_plan(
        client,
        [
            {
                "sku": "ANY-SKU",
                "quantity": 1,
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


def test_pick_plan_orders_boxes_by_physical_code_not_cart_order(
    client,
):
    products = [
        (
            "SKU-PICK-C",
            "Produto Box C",
            "LOT-C",
            "BOX-C1",
        ),
        (
            "SKU-PICK-A2",
            "Produto Box A2",
            "LOT-A2",
            "BOX-A2",
        ),
        (
            "SKU-PICK-B",
            "Produto Box B",
            "LOT-B",
            "BOX-B1",
        ),
        (
            "SKU-PICK-A1",
            "Produto Box A1",
            "LOT-A1",
            "BOX-A1",
        ),
    ]

    for sku, name, batch, location in products:
        create_product(
            client,
            sku,
            name=name,
        )

        receive_batch(
            client,
            sku=sku,
            batch=batch,
            quantity=10,
            expiration="2030-01-01",
        )

        putaway_batch(
            client,
            sku=sku,
            batch=batch,
            location=location,
        )

    response = request_pick_plan(
        client,
        [
            {
                "sku": "SKU-PICK-C",
                "quantity": 1,
            },
            {
                "sku": "SKU-PICK-A2",
                "quantity": 1,
            },
            {
                "sku": "SKU-PICK-B",
                "quantity": 1,
            },
            {
                "sku": "SKU-PICK-A1",
                "quantity": 1,
            },
        ],
    )

    assert response.status_code == 200
    assert response.is_json

    steps = response.json["steps"]

    assert [
        step["location_id"]
        for step in steps
    ] == [
        "BOX-A1",
        "BOX-A2",
        "BOX-B1",
        "BOX-C1",
    ]

    assert [
        step["sequence"]
        for step in steps
    ] == [
        1,
        2,
        3,
        4,
    ]


def test_pick_plan_preserves_fefo_allocations_when_reordering_route(
    client,
):
    sku = "SKU-PICK-FEFO"

    create_product(
        client,
        sku,
        name="Produto FEFO Coleta",
    )

    receive_batch(
        client,
        sku=sku,
        batch="LOT-FIRST",
        quantity=4,
        expiration="2029-01-01",
    )

    putaway_batch(
        client,
        sku=sku,
        batch="LOT-FIRST",
        location="BOX-C1",
    )

    receive_batch(
        client,
        sku=sku,
        batch="LOT-SECOND",
        quantity=10,
        expiration="2030-01-01",
    )

    putaway_batch(
        client,
        sku=sku,
        batch="LOT-SECOND",
        location="BOX-A1",
    )

    response = request_pick_plan(
        client,
        [
            {
                "sku": sku,
                "quantity": 7,
            }
        ],
    )

    assert response.status_code == 200

    steps = response.json["steps"]

    assert len(steps) == 2

    by_batch = {
        step["batch_code"]: step
        for step in steps
    }

    assert (
        by_batch["LOT-FIRST"]["quantity"]
        == 4
    )

    assert (
        by_batch["LOT-SECOND"]["quantity"]
        == 3
    )

    # Caminhada física pode começar no BOX-A1,
    # mas a seleção quantitativa continua FEFO.
    assert steps[0]["location_id"] == "BOX-A1"
    assert steps[1]["location_id"] == "BOX-C1"


def test_pick_plan_exposes_operational_fields(client):
    sku = "SKU-PICK-FIELDS"

    create_product(
        client,
        sku,
        name="Arroz Integral 1KG",
    )

    receive_batch(
        client,
        sku=sku,
        batch="LOT-FIELDS",
        quantity=8,
        expiration="2031-05-20",
    )

    putaway_batch(
        client,
        sku=sku,
        batch="LOT-FIELDS",
        location="BOX-D2",
    )

    response = request_pick_plan(
        client,
        [
            {
                "sku": sku,
                "quantity": 3,
            }
        ],
    )

    assert response.status_code == 200

    step = response.json["steps"][0]

    assert step["sequence"] == 1
    assert step["location_id"] == "BOX-D2"
    assert step["sku"] == sku
    assert step["name"] == "Arroz Integral 1KG"
    assert step["batch_code"] == "LOT-FIELDS"
    assert step["expiration_date"] == "2031-05-20"
    assert step["quantity"] == 3


def test_pick_plan_rejects_fefo_batch_without_physical_address(
    client,
):
    sku = "SKU-PICK-NOLOC"

    create_product(client, sku)

    receive_batch(
        client,
        sku=sku,
        batch="LOT-NOLOC",
        quantity=10,
        expiration="2029-06-01",
    )

    # Lote posterior possui endereço, mas não pode substituir
    # silenciosamente o lote FEFO ainda não endereçado.
    receive_batch(
        client,
        sku=sku,
        batch="LOT-ADDRESSED",
        quantity=10,
        expiration="2030-06-01",
    )

    putaway_batch(
        client,
        sku=sku,
        batch="LOT-ADDRESSED",
        location="BOX-B1",
    )

    response = request_pick_plan(
        client,
        [
            {
                "sku": sku,
                "quantity": 5,
            }
        ],
    )

    assert response.status_code == 400
    assert response.is_json

    assert (
        "endereçamento"
        in response.json["error"].lower()
        or
        "localização"
        in response.json["error"].lower()
    )


def test_pick_plan_does_not_mutate_stock(client):
    sku = "SKU-PICK-NOMUT"

    create_product(client, sku)

    receive_batch(
        client,
        sku=sku,
        batch="LOT-NOMUT",
        quantity=9,
        expiration="2031-09-01",
    )

    putaway_batch(
        client,
        sku=sku,
        batch="LOT-NOMUT",
        location="BOX-E1",
    )

    before = query_product(
        client,
        sku,
    )

    response = request_pick_plan(
        client,
        [
            {
                "sku": sku,
                "quantity": 6,
            }
        ],
    )

    assert response.status_code == 200

    after = query_product(
        client,
        sku,
    )

    assert before["quantity"] == 9
    assert after["quantity"] == 9

    assert (
        get_batch(
            before,
            "LOT-NOMUT",
        )["quantity"]
        == 9
    )

    assert (
        get_batch(
            after,
            "LOT-NOMUT",
        )["quantity"]
        == 9
    )


def test_pick_plan_keeps_steps_from_same_box_adjacent(
    client,
):
    definitions = [
        (
            "SKU-PICK-SAME-1",
            "Produto Um",
            "LOT-SAME-1",
            "BOX-B2",
        ),
        (
            "SKU-PICK-OTHER",
            "Produto Outro",
            "LOT-OTHER",
            "BOX-A1",
        ),
        (
            "SKU-PICK-SAME-2",
            "Produto Dois",
            "LOT-SAME-2",
            "BOX-B2",
        ),
    ]

    for sku, name, batch, location in definitions:
        create_product(
            client,
            sku,
            name=name,
        )

        receive_batch(
            client,
            sku=sku,
            batch=batch,
            quantity=5,
            expiration="2032-01-01",
        )

        putaway_batch(
            client,
            sku=sku,
            batch=batch,
            location=location,
        )

    response = request_pick_plan(
        client,
        [
            {
                "sku": "SKU-PICK-SAME-1",
                "quantity": 1,
            },
            {
                "sku": "SKU-PICK-OTHER",
                "quantity": 1,
            },
            {
                "sku": "SKU-PICK-SAME-2",
                "quantity": 1,
            },
        ],
    )

    assert response.status_code == 200

    locations = [
        step["location_id"]
        for step in response.json["steps"]
    ]

    assert locations == [
        "BOX-A1",
        "BOX-B2",
        "BOX-B2",
    ]
