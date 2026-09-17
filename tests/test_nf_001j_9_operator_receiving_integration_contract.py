"""
NF-001J.9 — Operator Receiving Integration Contract.
"""

import importlib

import pytest

from src.domain.product import Product
from src.infrastructure.config import Config
from src.infrastructure.container import Container


@pytest.fixture
def application_module(
    monkeypatch,
    tmp_path,
):
    """
    Provide the canonical Flask gateway with a fresh
    Container for every J.9 test.

    app.py itself remains canonical and is imported once.
    Only its composition root is temporarily replaced.

    This prevents cached repository/use-case state from
    leaking between tests while preserving production
    composition semantics.
    """

    monkeypatch.setenv(
        "KIPPE_ENV",
        "testing",
    )
    monkeypatch.setenv(
        "KIPPE_DB_PATH",
        str(tmp_path / "nf001j9.db"),
    )
    monkeypatch.setenv(
        "KIPPE_LOG_PATH",
        str(tmp_path / "nf001j9.log"),
    )

    module = importlib.import_module(
        "app"
    )

    original_container = module.container

    test_config = Config()
    test_container = Container(
        config_override=test_config
    )

    module.container = test_container

    module.app.config.update(
        TESTING=True,
    )

    try:
        yield module
    finally:
        module.container = original_container


@pytest.fixture
def client(application_module):
    return application_module.app.test_client()


def headers():
    return {
        "X-Test-Operator-Override": "ADM-J9"
    }


def invoice_payload(
    *,
    quantity=12,
):
    return {
        "invoice_number": "NF-J9-001",
        "supplier_id": "MULTICOM",
        "access_key": "9" * 44,
        "series": "1",
        "origin_document": "OCR",
        "lines": [
            {
                "supplier_product_code": (
                    "FORN-J9-001"
                ),
                "description": (
                    "CREME CHANTILY AMELIA "
                    "CHANTY MIX 200ML SCH"
                ),
                "gtin": "7896096013542",
                "commercial_unit": "UN",
                "quantity": quantity,
                "unit_price": 1.0,
            }
        ],
    }


def certified_payload(
    *,
    quantity=12,
):
    return {
        "invoice": invoice_payload(
            quantity=quantity
        ),
        "conference": {
            "counts": {
                "1": quantity,
            },
            "physical_data": {
                "1": {
                    "batch_code": "LN2SP",
                    "expiration_date": (
                        "2027-01-13"
                    ),
                    "manufacturing_date": "",
                }
            },
        },
    }


def seed_product(application_module):
    repository = (
        application_module
        .container
        .product_repository
    )

    existing = repository.get_by_ean(
        "7896096013542"
    )

    if existing is None:
        repository.save(
            Product(
                id="SKU-J9-001",
                name=(
                    "CREME CHANTILY AMELIA "
                    "CHANTY MIX 200ML SCH"
                ),
                ean="7896096013542",
            )
        )

    return repository


def stock_quantity(repository):
    product = repository.get_by_ean(
        "7896096013542"
    )

    return product.quantity


def test_certified_endpoint_exists(
    client,
):
    response = client.post(
        "/api/invoices/receive-certified",
        json={},
        headers=headers(),
    )

    assert response.status_code != 404


def test_certified_endpoint_requires_operator(
    client,
):
    response = client.post(
        "/api/invoices/receive-certified",
        json=certified_payload(),
    )

    assert response.status_code == 401


def test_unknown_product_is_blocked_before_stock(
    client,
    application_module,
):
    repository = (
        application_module
        .container
        .product_repository
    )

    assert repository.get_by_ean(
        "7896096013542"
    ) is None

    response = client.post(
        "/api/invoices/receive-certified",
        json=certified_payload(),
        headers=headers(),
    )

    assert response.status_code == 400

    assert repository.get_by_ean(
        "7896096013542"
    ) is None


def test_first_certified_execution_receives_once(
    client,
    application_module,
):
    repository = seed_product(
        application_module
    )

    assert stock_quantity(
        repository
    ) == 0

    response = client.post(
        "/api/invoices/receive-certified",
        json=certified_payload(),
        headers=headers(),
    )

    assert response.status_code == 200

    body = response.get_json()

    assert body["invoice_number"] == "NF-J9-001"
    assert body["supplier_id"] == "MULTICOM"
    assert body["conference_closed_by"] == "ADM-J9"
    assert body["executed_lines"] == 1
    assert body["replay_lines"] == 0

    line = body["lines"][0]

    assert line["status"] == "NEW"
    assert line["executed"] is True
    assert line["operation_status"] == "COMPLETED"

    assert stock_quantity(
        repository
    ) == 12


def test_replay_does_not_receive_twice(
    client,
    application_module,
):
    repository = seed_product(
        application_module
    )

    first = client.post(
        "/api/invoices/receive-certified",
        json=certified_payload(),
        headers=headers(),
    )

    second = client.post(
        "/api/invoices/receive-certified",
        json=certified_payload(),
        headers=headers(),
    )

    assert first.status_code == 200
    assert second.status_code == 200

    body = second.get_json()

    assert body["executed_lines"] == 0
    assert body["replay_lines"] == 1

    assert body["lines"][0]["status"] == "REPLAY"
    assert body["lines"][0]["executed"] is False

    assert stock_quantity(
        repository
    ) == 12


def test_conflicting_replay_does_not_mutate_stock(
    client,
    application_module,
):
    repository = seed_product(
        application_module
    )

    first = client.post(
        "/api/invoices/receive-certified",
        json=certified_payload(
            quantity=12
        ),
        headers=headers(),
    )

    assert first.status_code == 200
    assert stock_quantity(repository) == 12

    conflict = client.post(
        "/api/invoices/receive-certified",
        json=certified_payload(
            quantity=11
        ),
        headers=headers(),
    )

    assert conflict.status_code == 200

    body = conflict.get_json()

    assert body["executed_lines"] == 0
    assert body["lines"][0]["status"] == "CONFLICT"
    assert body["lines"][0]["executed"] is False

    assert stock_quantity(repository) == 12


def test_zero_physical_quantity_does_not_receive(
    client,
    application_module,
):
    repository = seed_product(
        application_module
    )

    payload = certified_payload()

    payload["conference"]["counts"]["1"] = 0
    payload["conference"]["physical_data"] = {}

    response = client.post(
        "/api/invoices/receive-certified",
        json=payload,
        headers=headers(),
    )

    assert response.status_code == 200

    body = response.get_json()

    assert body["executed_lines"] == 0
    assert (
        body["skipped_zero_quantity_lines"]
        == 1
    )

    assert stock_quantity(repository) == 0


def test_missing_physical_count_is_rejected(
    client,
    application_module,
):
    repository = seed_product(
        application_module
    )

    payload = certified_payload()
    payload["conference"]["counts"] = {}

    response = client.post(
        "/api/invoices/receive-certified",
        json=payload,
        headers=headers(),
    )

    assert response.status_code == 400
    assert stock_quantity(repository) == 0


def test_missing_lot_is_rejected_without_stock(
    client,
    application_module,
):
    repository = seed_product(
        application_module
    )

    payload = certified_payload()

    payload[
        "conference"
    ][
        "physical_data"
    ][
        "1"
    ][
        "batch_code"
    ] = ""

    response = client.post(
        "/api/invoices/receive-certified",
        json=payload,
        headers=headers(),
    )

    assert response.status_code == 400
    assert stock_quantity(repository) == 0


def test_documentary_reconciliation_remains_read_only(
    client,
    application_module,
):
    repository = seed_product(
        application_module
    )

    response = client.post(
        "/api/invoices/reconcile",
        json=invoice_payload(),
    )

    assert response.status_code == 200
    assert stock_quantity(repository) == 0


def test_legacy_receive_endpoint_still_exists(
    client,
):
    response = client.post(
        "/api/receive",
        json={},
        headers=headers(),
    )

    assert response.status_code != 404
