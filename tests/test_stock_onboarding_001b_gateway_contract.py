import json
import os
from pathlib import Path

import pytest

from src.infrastructure.config import Config


ENDPOINT = "/api/stock/onboarding"


MANAGER_HEADERS = {
    "X-Test-Operator-Override": (
        "SYSTEM-TEST-MANAGER"
    ),
    "X-Test-Role-Override": "GERENTE",
}


ADMIN_HEADERS = {
    "X-Test-Operator-Override": (
        "SYSTEM-TEST-ADMIN"
    ),
    "X-Test-Role-Override": (
        "ADMIN_SISTEMA"
    ),
}


OPERATOR_HEADERS = {
    "X-Test-Operator-Override": (
        "SYSTEM-TEST-OPERATOR"
    ),
    "X-Test-Role-Override": "OPERADOR",
}


@pytest.fixture
def client():
    from app import app, container

    test_config = Config.for_testing()

    container.config = test_config

    for attribute in (
        "_logger",
        "_product_repository",
        "_operator_repository",
        "_manage_stock_use_case",
        "_manage_operators_use_case",
        "_receiving_use_case",
        "_existing_stock_onboarding_use_case",
    ):
        if hasattr(
            container,
            attribute,
        ):
            setattr(
                container,
                attribute,
                None,
            )

    container.product_repository._init_db()

    app.config[
        "TESTING"
    ] = True

    app.secret_key = (
        test_config.SECRET_KEY
    )

    with app.test_client() as test_client:
        yield test_client

    for path in (
        test_config.DB_PATH,
        test_config.LOG_PATH,
    ):
        if (
            path
            and os.path.exists(path)
        ):
            os.remove(path)


def _create_product(
    client,
    *,
    product_id,
    headers=MANAGER_HEADERS,
):
    response = client.post(
        "/api/produto",
        json={
            "id": product_id,
            "name": (
                "PRODUTO ESTOQUE "
                "PREEXISTENTE TESTE"
            ),
            "unit_of_measure": "un",
            "status": "ATIVO",
        },
        headers=headers,
    )

    assert response.status_code == 201

    return response


def _payload(
    *,
    product_id="LEGACY-HTTP-001",
    **overrides,
):
    payload = {
        "sku": product_id,
        "quantity": 12,
        "batch_code": "LEG-HTTP-001",
        "expiration_date": "2027-06-30",
        "manufacturing_date": "",
        "supplier": "",
        "location_id": "",
        "historical_receipt_date": None,
        "historical_date_basis": None,
        "document_id": "",
    }

    payload.update(
        overrides
    )

    return payload


def test_gateway_registers_post_route():
    from app import app

    rules = {
        (
            rule.rule,
            tuple(
                sorted(
                    method
                    for method
                    in rule.methods
                    if method not in {
                        "HEAD",
                        "OPTIONS",
                    }
                )
            ),
        )
        for rule in app.url_map.iter_rules()
    }

    assert (
        ENDPOINT,
        (
            "POST",
        ),
    ) in rules


def test_gateway_rejects_unauthenticated_request(
    client,
):
    response = client.post(
        ENDPOINT,
        json=_payload(),
    )

    assert response.status_code == 401

    assert (
        "Operador não autenticado"
        in response.json[
            "error"
        ]
    )


def test_manager_can_onboard_existing_stock(
    client,
):
    product_id = "LEGACY-HTTP-MANAGER"

    _create_product(
        client,
        product_id=product_id,
    )

    response = client.post(
        ENDPOINT,
        json=_payload(
            product_id=product_id,
        ),
        headers=MANAGER_HEADERS,
    )

    assert response.status_code == 200

    assert response.json[
        "message"
    ] == (
        "Estoque existente incorporado."
    )


def test_system_admin_can_onboard_existing_stock(
    client,
):
    product_id = "LEGACY-HTTP-ADMIN"

    _create_product(
        client,
        product_id=product_id,
        headers=ADMIN_HEADERS,
    )

    response = client.post(
        ENDPOINT,
        json=_payload(
            product_id=product_id,
        ),
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200


def test_operator_is_forbidden(
    client,
):
    product_id = "LEGACY-HTTP-OPERATOR"

    _create_product(
        client,
        product_id=product_id,
    )

    response = client.post(
        ENDPOINT,
        json=_payload(
            product_id=product_id,
        ),
        headers=OPERATOR_HEADERS,
    )

    assert response.status_code == 403

    assert response.json[
        "error"
    ]


def test_success_response_exposes_explicit_onboarding_semantics(
    client,
):
    product_id = "LEGACY-HTTP-SEMANTICS"

    _create_product(
        client,
        product_id=product_id,
    )

    response = client.post(
        ENDPOINT,
        json=_payload(
            product_id=product_id,
            quantity=17,
            batch_code="LEG-SEM-01",
        ),
        headers=MANAGER_HEADERS,
    )

    assert response.status_code == 200

    onboarding = response.json[
        "onboarding"
    ]

    assert onboarding[
        "status"
    ] == "STOCK_ONBOARDED"

    assert onboarding[
        "event_type"
    ] == "IMPLANTACAO_ESTOQUE"

    assert onboarding[
        "sku"
    ] == product_id

    assert onboarding[
        "batch_code"
    ] == "LEG-SEM-01"

    assert onboarding[
        "quantity"
    ] == 17

    assert onboarding[
        "quantity_before"
    ] == 0

    assert onboarding[
        "quantity_after"
    ] == 17


def test_gateway_updates_canonical_product_quantity(
    client,
):
    product_id = "LEGACY-HTTP-STOCK"

    _create_product(
        client,
        product_id=product_id,
    )

    response = client.post(
        ENDPOINT,
        json=_payload(
            product_id=product_id,
            quantity=23,
        ),
        headers=MANAGER_HEADERS,
    )

    assert response.status_code == 200

    product = client.get(
        f"/api/produto/{product_id}"
    )

    assert product.status_code == 200

    assert product.json[
        "quantity"
    ] == 23


def test_gateway_creates_implantacao_audit_not_recebimento(
    client,
):
    from app import container

    product_id = "LEGACY-HTTP-AUDIT"

    _create_product(
        client,
        product_id=product_id,
    )

    response = client.post(
        ENDPOINT,
        json=_payload(
            product_id=product_id,
        ),
        headers=MANAGER_HEADERS,
    )

    assert response.status_code == 200

    events = (
        container.product_repository
        .get_operational_audit_events_by_product(
            product_id
        )
    )

    assert len(events) == 1

    assert (
        events[0][
            "event_type"
        ]
        == "IMPLANTACAO_ESTOQUE"
    )

    assert all(
        event[
            "event_type"
        ]
        != "RECEBIMENTO"
        for event in events
    )


def test_gateway_preserves_historical_context_as_metadata(
    client,
):
    from app import container

    product_id = "LEGACY-HTTP-HISTORY"

    _create_product(
        client,
        product_id=product_id,
    )

    response = client.post(
        ENDPOINT,
        json=_payload(
            product_id=product_id,
            historical_receipt_date=(
                "2026-08-20"
            ),
            historical_date_basis=(
                "DOCUMENT"
            ),
            document_id="NF-LEGADA-900",
        ),
        headers=MANAGER_HEADERS,
    )

    assert response.status_code == 200

    event = (
        container.product_repository
        .get_operational_audit_events_by_product(
            product_id
        )[0]
    )

    metadata = json.loads(
        event[
            "metadata_json"
        ]
    )

    assert (
        metadata[
            "historical_receipt_date"
        ]
        == "2026-08-20"
    )

    assert (
        metadata[
            "historical_date_basis"
        ]
        == "DOCUMENT"
    )

    assert (
        event[
            "document_id"
        ]
        == "NF-LEGADA-900"
    )

    assert not str(
        event[
            "occurred_at"
        ]
    ).startswith(
        "2026-08-20"
    )


def test_gateway_unknown_product_is_bad_request(
    client,
):
    response = client.post(
        ENDPOINT,
        json=_payload(
            product_id=(
                "SKU-NAO-EXISTE"
            ),
        ),
        headers=MANAGER_HEADERS,
    )

    assert response.status_code == 400

    assert response.json[
        "error"
    ]


def test_gateway_zero_quantity_is_bad_request(
    client,
):
    product_id = "LEGACY-HTTP-ZERO"

    _create_product(
        client,
        product_id=product_id,
    )

    response = client.post(
        ENDPOINT,
        json=_payload(
            product_id=product_id,
            quantity=0,
        ),
        headers=MANAGER_HEADERS,
    )

    assert response.status_code == 400


def test_gateway_missing_batch_is_bad_request(
    client,
):
    product_id = "LEGACY-HTTP-NOBATCH"

    _create_product(
        client,
        product_id=product_id,
    )

    response = client.post(
        ENDPOINT,
        json=_payload(
            product_id=product_id,
            batch_code="",
        ),
        headers=MANAGER_HEADERS,
    )

    assert response.status_code == 400


def test_gateway_historical_date_without_basis_is_bad_request(
    client,
):
    product_id = "LEGACY-HTTP-DATE"

    _create_product(
        client,
        product_id=product_id,
    )

    response = client.post(
        ENDPOINT,
        json=_payload(
            product_id=product_id,
            historical_receipt_date=(
                "2026-08-20"
            ),
            historical_date_basis=None,
        ),
        headers=MANAGER_HEADERS,
    )

    assert response.status_code == 400


def test_gateway_document_basis_requires_document_number(
    client,
):
    product_id = "LEGACY-HTTP-DOC"

    _create_product(
        client,
        product_id=product_id,
    )

    response = client.post(
        ENDPOINT,
        json=_payload(
            product_id=product_id,
            historical_receipt_date=(
                "2026-08-20"
            ),
            historical_date_basis=(
                "DOCUMENT"
            ),
            document_id="",
        ),
        headers=MANAGER_HEADERS,
    )

    assert response.status_code == 400


def test_gateway_source_is_independent_from_receiving_route():
    source = Path(
        "app.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "/api/stock/onboarding"
        in source
    )

    marker = (
        "@app.route("
        "'/api/stock/onboarding'"
    )

    if marker not in source:
        marker = (
            '@app.route('
            '"/api/stock/onboarding"'
        )

    start = source.index(
        marker
    )

    tail = source[
        start:
    ]

    next_route = tail.find(
        "@app.route(",
        len(marker),
    )

    region = (
        tail
        if next_route == -1
        else tail[
            :next_route
        ]
    )

    assert (
        "existing_stock_onboarding"
        in region
    )

    assert (
        "receive_use_case"
        not in region
    )

    assert (
        "/api/receive"
        not in region
    )
