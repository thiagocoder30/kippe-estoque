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
    name="Produto Abastecimento",
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


def confirm_pick(
    client,
    *,
    sku,
    batch,
    quantity,
    authenticated=True,
):
    headers = (
        auth_headers()
        if authenticated
        else {}
    )

    return client.post(
        "/api/abastecimento/coleta/confirmar",
        json={
            "sku": sku,
            "batch_code": batch,
            "quantity": quantity,
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


def history(client):
    response = client.get(
        "/api/historico"
    )

    assert response.status_code == 200
    assert response.is_json

    return response.json


def test_confirm_pick_requires_authentication(client):
    response = confirm_pick(
        client,
        sku="ANY-SKU",
        batch="ANY-LOT",
        quantity=1,
        authenticated=False,
    )

    assert response.status_code == 401
    assert response.is_json

    assert (
        response.json["error"]
        == "Operador não autenticado."
    )


def test_confirm_pick_decrements_exact_physical_batch(
    client,
):
    sku = "SKU-CONFIRM-EXACT"

    create_product(client, sku)

    # Este vence primeiro.
    receive_batch(
        client,
        sku=sku,
        batch="LOT-FIRST",
        quantity=5,
        expiration="2029-01-01",
    )

    putaway_batch(
        client,
        sku=sku,
        batch="LOT-FIRST",
        location="BOX-A1",
    )

    # Este vence depois.
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
        location="BOX-B1",
    )

    # A confirmação física aponta explicitamente para LOT-SECOND.
    response = confirm_pick(
        client,
        sku=sku,
        batch="LOT-SECOND",
        quantity=3,
    )

    assert response.status_code == 200
    assert response.is_json

    product = query_product(
        client,
        sku,
    )

    assert product["quantity"] == 12

    assert (
        get_batch(
            product,
            "LOT-FIRST",
        )["quantity"]
        == 5
    )

    assert (
        get_batch(
            product,
            "LOT-SECOND",
        )["quantity"]
        == 7
    )


def test_confirm_pick_uses_confirmed_not_planned_quantity(
    client,
):
    sku = "SKU-CONFIRM-PARTIAL"

    create_product(client, sku)

    receive_batch(
        client,
        sku=sku,
        batch="LOT-PARTIAL",
        quantity=10,
        expiration="2030-03-01",
    )

    putaway_batch(
        client,
        sku=sku,
        batch="LOT-PARTIAL",
        location="BOX-C1",
    )

    # O plano poderia ter pedido 10.
    # A verdade física confirmada é 7.
    response = confirm_pick(
        client,
        sku=sku,
        batch="LOT-PARTIAL",
        quantity=7,
    )

    assert response.status_code == 200

    payload = response.json

    assert payload["sku"] == sku
    assert payload["batch_code"] == "LOT-PARTIAL"
    assert payload["confirmed_quantity"] == 7
    assert payload["remaining_batch_quantity"] == 3
    assert payload["remaining_product_quantity"] == 3

    product = query_product(
        client,
        sku,
    )

    assert product["quantity"] == 3

    assert (
        get_batch(
            product,
            "LOT-PARTIAL",
        )["quantity"]
        == 3
    )


def test_confirm_pick_can_zero_batch_and_keep_it_persisted(
    client,
):
    sku = "SKU-CONFIRM-ZERO"

    create_product(client, sku)

    receive_batch(
        client,
        sku=sku,
        batch="LOT-ZERO",
        quantity=4,
        expiration="2031-06-15",
    )

    putaway_batch(
        client,
        sku=sku,
        batch="LOT-ZERO",
        location="BOX-D1",
    )

    response = confirm_pick(
        client,
        sku=sku,
        batch="LOT-ZERO",
        quantity=4,
    )

    assert response.status_code == 200

    first = query_product(
        client,
        sku,
    )

    assert first["quantity"] == 0

    zero_batch = get_batch(
        first,
        "LOT-ZERO",
    )

    assert zero_batch["quantity"] == 0
    assert zero_batch["expiration_date"] == "2031-06-15"

    from app import container

    container._product_repository = None

    reloaded = (
        container.product_repository
        .get_by_id(sku)
    )

    assert reloaded is not None
    assert "LOT-ZERO" in reloaded.batches

    assert (
        reloaded
        .batches["LOT-ZERO"]
        .quantity
        == 0
    )


def test_confirm_pick_zero_batch_remains_in_expiration_report(
    client,
):
    sku = "SKU-CONFIRM-EXP"

    create_product(client, sku)

    receive_batch(
        client,
        sku=sku,
        batch="LOT-EXP",
        quantity=3,
        expiration="2031-08-20",
    )

    putaway_batch(
        client,
        sku=sku,
        batch="LOT-EXP",
        location="BOX-E1",
    )

    response = confirm_pick(
        client,
        sku=sku,
        batch="LOT-EXP",
        quantity=3,
    )

    assert response.status_code == 200

    report = client.get(
        "/api/relatorios/vencimentos"
    )

    assert report.status_code == 200

    matches = [
        item
        for item in report.json
        if item["sku"] == sku
        and item["batch"] == "LOT-EXP"
    ]

    assert len(matches) == 1
    assert matches[0]["quantity"] == 0
    assert matches[0]["expiration"] == "2031-08-20"


def test_confirm_pick_records_replenishment_business_semantics(
    client,
):
    sku = "SKU-CONFIRM-HISTORY"

    create_product(client, sku)

    receive_batch(
        client,
        sku=sku,
        batch="LOT-HISTORY",
        quantity=8,
        expiration="2032-01-01",
    )

    putaway_batch(
        client,
        sku=sku,
        batch="LOT-HISTORY",
        location="BOX-F1",
    )

    response = confirm_pick(
        client,
        sku=sku,
        batch="LOT-HISTORY",
        quantity=5,
    )

    assert response.status_code == 200

    rows = history(client)

    matches = [
        row
        for row in rows
        if row["name"] == "Produto Abastecimento"
        and "ABASTECIMENTO_LOJA" in row["type"]
    ]

    assert len(matches) == 1

    movement = matches[0]

    assert movement["amount"] == 5
    assert movement["operator_id"] == "SYSTEM-TEST-AGENT"

    assert "LOT-HISTORY" in movement["type"]

    assert "SAIDA" not in movement["type"].upper()
    assert "SALE" not in movement["type"].upper()
    assert "TRANSFER" not in movement["type"].upper()


@pytest.mark.parametrize(
    "quantity",
    [
        0,
        -1,
    ],
)
def test_confirm_pick_rejects_non_positive_quantity_without_mutation(
    client,
    quantity,
):
    sku = f"SKU-CONFIRM-QTY-{abs(quantity)}"

    create_product(client, sku)

    receive_batch(
        client,
        sku=sku,
        batch="LOT-QTY",
        quantity=5,
        expiration="2032-02-01",
    )

    putaway_batch(
        client,
        sku=sku,
        batch="LOT-QTY",
        location="BOX-G1",
    )

    before = query_product(
        client,
        sku,
    )

    response = confirm_pick(
        client,
        sku=sku,
        batch="LOT-QTY",
        quantity=quantity,
    )

    assert response.status_code == 400

    after = query_product(
        client,
        sku,
    )

    assert after["quantity"] == before["quantity"]

    assert (
        get_batch(
            after,
            "LOT-QTY",
        )["quantity"]
        == 5
    )


def test_confirm_pick_rejects_quantity_above_batch_stock_without_mutation(
    client,
):
    sku = "SKU-CONFIRM-OVER"

    create_product(client, sku)

    receive_batch(
        client,
        sku=sku,
        batch="LOT-OVER",
        quantity=5,
        expiration="2032-03-01",
    )

    putaway_batch(
        client,
        sku=sku,
        batch="LOT-OVER",
        location="BOX-H1",
    )

    before = query_product(
        client,
        sku,
    )

    response = confirm_pick(
        client,
        sku=sku,
        batch="LOT-OVER",
        quantity=6,
    )

    assert response.status_code == 400

    after = query_product(
        client,
        sku,
    )

    assert after["quantity"] == before["quantity"]

    assert (
        get_batch(
            after,
            "LOT-OVER",
        )["quantity"]
        == 5
    )


def test_confirm_pick_rejects_unknown_batch_without_mutation(
    client,
):
    sku = "SKU-CONFIRM-NOBATCH"

    create_product(client, sku)

    receive_batch(
        client,
        sku=sku,
        batch="LOT-REAL",
        quantity=5,
        expiration="2032-04-01",
    )

    putaway_batch(
        client,
        sku=sku,
        batch="LOT-REAL",
        location="BOX-I1",
    )

    before = query_product(
        client,
        sku,
    )

    response = confirm_pick(
        client,
        sku=sku,
        batch="LOT-UNKNOWN",
        quantity=2,
    )

    assert response.status_code == 400

    after = query_product(
        client,
        sku,
    )

    assert after["quantity"] == before["quantity"]

    assert (
        get_batch(
            after,
            "LOT-REAL",
        )["quantity"]
        == 5
    )


def test_confirm_pick_rejects_unaddressed_batch(
    client,
):
    sku = "SKU-CONFIRM-NOLOC"

    create_product(client, sku)

    receive_batch(
        client,
        sku=sku,
        batch="LOT-NOLOC",
        quantity=5,
        expiration="2032-05-01",
    )

    response = confirm_pick(
        client,
        sku=sku,
        batch="LOT-NOLOC",
        quantity=2,
    )

    assert response.status_code == 400

    assert (
        "endereçamento"
        in response.json["error"].lower()
        or
        "localização"
        in response.json["error"].lower()
    )

    product = query_product(
        client,
        sku,
    )

    assert product["quantity"] == 5
    assert (
        get_batch(
            product,
            "LOT-NOLOC",
        )["quantity"]
        == 5
    )

def test_rejected_confirm_pick_does_not_record_replenishment_transaction(
    client,
):
    sku = "SKU-CONFIRM-REJECT-HISTORY"

    create_product(client, sku)

    receive_batch(
        client,
        sku=sku,
        batch="LOT-REJECT-HISTORY",
        quantity=5,
        expiration="2032-06-01",
    )

    putaway_batch(
        client,
        sku=sku,
        batch="LOT-REJECT-HISTORY",
        location="BOX-J1",
    )

    before = history(client)

    response = confirm_pick(
        client,
        sku=sku,
        batch="LOT-REJECT-HISTORY",
        quantity=6,
    )

    assert response.status_code == 400

    after = history(client)

    before_replenishment = [
        row
        for row in before
        if "ABASTECIMENTO_LOJA"
        in row["type"].upper()
    ]

    after_replenishment = [
        row
        for row in after
        if "ABASTECIMENTO_LOJA"
        in row["type"].upper()
    ]

    assert after_replenishment == before_replenishment

    product = query_product(
        client,
        sku,
    )

    assert product["quantity"] == 5

    assert (
        get_batch(
            product,
            "LOT-REJECT-HISTORY",
        )["quantity"]
        == 5
    )

