import json
import sqlite3
from pathlib import Path

import pytest

from src.domain.access_control import AccessControl
from src.domain.product import Product
from src.interfaces.sqlite_repository import (
    SQLiteProductRepository,
)


TEST_DB = Path(
    "data/stock_onboarding_001a_contract.db"
)


class IdentityStub:
    def __init__(
        self,
        *,
        operator_id="1001",
        role=AccessControl.ROLE_SYSTEM_ADMIN,
    ):
        self.operator_id = operator_id
        self.role = role

    def get_current_operator_id(self):
        return self.operator_id

    def get_current_operator_role(self):
        return self.role


@pytest.fixture
def repository():
    TEST_DB.unlink(
        missing_ok=True
    )

    repo = SQLiteProductRepository(
        str(TEST_DB)
    )

    yield repo

    TEST_DB.unlink(
        missing_ok=True
    )


def _create_product(
    repository,
    *,
    product_id="SKU-LEGACY-001",
):
    product = Product(
        id=product_id,
        name="PRODUTO LEGADO TESTE",
        ean="7890000000001",
        quantity=0,
        unit_of_measure="un",
        status="ATIVO",
    )

    repository.save(
        product
    )

    return product


def _use_case(
    repository,
    *,
    role=AccessControl.ROLE_SYSTEM_ADMIN,
):
    from src.use_cases.existing_stock_onboarding import (
        ExistingStockOnboardingUseCase,
    )

    return ExistingStockOnboardingUseCase(
        repository=repository,
        identity_provider=IdentityStub(
            role=role
        ),
    )


def _execute(
    use_case,
    **overrides,
):
    payload = {
        "product_id": "SKU-LEGACY-001",
        "quantity": 12,
        "batch_code": "LEG-001",
        "expiration_date": "2027-01-31",
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

    return use_case.execute(
        **payload
    )


def _events(
    repository,
    product_id="SKU-LEGACY-001",
):
    return (
        repository
        .get_operational_audit_events_by_product(
            product_id
        )
    )


def test_onboarding_use_case_exists():
    from src.use_cases.existing_stock_onboarding import (
        ExistingStockOnboardingUseCase,
    )

    assert ExistingStockOnboardingUseCase


def test_catalog_registration_and_onboarding_remain_distinct(
    repository,
):
    product = _create_product(
        repository
    )

    assert product.quantity == 0

    assert _events(
        repository
    ) == []


def test_existing_stock_onboarding_adds_authoritative_product_and_batch_quantity(
    repository,
):
    _create_product(
        repository
    )

    result = _execute(
        _use_case(repository)
    )

    assert result.is_success

    product = repository.get_by_id(
        "SKU-LEGACY-001"
    )

    assert product.quantity == 12

    assert (
        product.batches[
            "LEG-001"
        ].quantity
        == 12
    )


def test_onboarding_creates_implantacao_event_not_recebimento(
    repository,
):
    _create_product(
        repository
    )

    result = _execute(
        _use_case(repository)
    )

    assert result.is_success

    events = _events(
        repository
    )

    assert len(events) == 1

    assert (
        events[0][
            "event_type"
        ]
        == "IMPLANTACAO_ESTOQUE"
    )

    assert all(
        event["event_type"]
        != "RECEBIMENTO"
        for event in events
    )


def test_onboarding_records_before_after_and_actual_quantity(
    repository,
):
    _create_product(
        repository
    )

    result = _execute(
        _use_case(repository),
        quantity=17,
    )

    assert result.is_success

    event = _events(
        repository
    )[0]

    assert event[
        "quantity_before"
    ] == 0

    assert event[
        "quantity_actual"
    ] == 17

    assert event[
        "quantity_after"
    ] == 17


def test_onboarding_metadata_marks_physical_count_and_legacy_stock(
    repository,
):
    _create_product(
        repository
    )

    result = _execute(
        _use_case(repository)
    )

    assert result.is_success

    event = _events(
        repository
    )[0]

    metadata = json.loads(
        event[
            "metadata_json"
        ]
    )

    assert (
        metadata[
            "inventory_source"
        ]
        == "PHYSICAL_COUNT"
    )

    assert (
        metadata[
            "legacy_stock"
        ]
        is True
    )


def test_unknown_historical_receipt_date_remains_null(
    repository,
):
    _create_product(
        repository
    )

    result = _execute(
        _use_case(repository),
        historical_receipt_date=None,
        historical_date_basis=None,
    )

    assert result.is_success

    metadata = json.loads(
        _events(repository)[0][
            "metadata_json"
        ]
    )

    assert (
        metadata[
            "historical_receipt_date"
        ]
        is None
    )

    assert (
        metadata[
            "historical_date_basis"
        ]
        is None
    )


def test_historical_date_is_documentary_metadata_not_occurred_at_override(
    repository,
):
    _create_product(
        repository
    )

    historical_date = (
        "2026-08-21"
    )

    result = _execute(
        _use_case(repository),
        historical_receipt_date=(
            historical_date
        ),
        historical_date_basis=(
            "DOCUMENT"
        ),
        document_id="NF-LEGADA-88",
    )

    assert result.is_success

    event = _events(
        repository
    )[0]

    metadata = json.loads(
        event[
            "metadata_json"
        ]
    )

    assert (
        metadata[
            "historical_receipt_date"
        ]
        == historical_date
    )

    assert (
        event[
            "occurred_at"
        ]
        != historical_date
    )

    assert not str(
        event["occurred_at"]
    ).startswith(
        historical_date
    )


@pytest.mark.parametrize(
    "basis",
    [
        "DOCUMENT",
        "OPERATOR_DECLARATION",
    ],
)
def test_supported_historical_date_basis_is_preserved(
    repository,
    basis,
):
    _create_product(
        repository
    )

    kwargs = {
        "historical_receipt_date": (
            "2026-08-20"
        ),
        "historical_date_basis": basis,
    }

    if basis == "DOCUMENT":
        kwargs[
            "document_id"
        ] = "NF-100"

    result = _execute(
        _use_case(repository),
        **kwargs,
    )

    assert result.is_success

    metadata = json.loads(
        _events(repository)[0][
            "metadata_json"
        ]
    )

    assert (
        metadata[
            "historical_date_basis"
        ]
        == basis
    )


def test_historical_date_requires_basis(
    repository,
):
    _create_product(
        repository
    )

    result = _execute(
        _use_case(repository),
        historical_receipt_date=(
            "2026-08-20"
        ),
        historical_date_basis=None,
    )

    assert not result.is_success

    assert _events(
        repository
    ) == []

    assert (
        repository.get_by_id(
            "SKU-LEGACY-001"
        ).quantity
        == 0
    )


def test_basis_without_historical_date_is_rejected(
    repository,
):
    _create_product(
        repository
    )

    result = _execute(
        _use_case(repository),
        historical_receipt_date=None,
        historical_date_basis=(
            "OPERATOR_DECLARATION"
        ),
    )

    assert not result.is_success

    assert _events(
        repository
    ) == []


def test_document_basis_requires_business_document_number(
    repository,
):
    _create_product(
        repository
    )

    result = _execute(
        _use_case(repository),
        historical_receipt_date=(
            "2026-08-20"
        ),
        historical_date_basis=(
            "DOCUMENT"
        ),
        document_id="",
    )

    assert not result.is_success

    assert _events(
        repository
    ) == []


def test_invalid_historical_date_basis_is_rejected(
    repository,
):
    _create_product(
        repository
    )

    result = _execute(
        _use_case(repository),
        historical_receipt_date=(
            "2026-08-20"
        ),
        historical_date_basis=(
            "GUESS"
        ),
    )

    assert not result.is_success

    assert _events(
        repository
    ) == []


def test_historical_receipt_date_must_be_iso_date(
    repository,
):
    _create_product(
        repository
    )

    result = _execute(
        _use_case(repository),
        historical_receipt_date=(
            "20/08/2026"
        ),
        historical_date_basis=(
            "OPERATOR_DECLARATION"
        ),
    )

    assert not result.is_success

    assert _events(
        repository
    ) == []


def test_future_historical_receipt_date_is_rejected(
    repository,
):
    _create_product(
        repository
    )

    result = _execute(
        _use_case(repository),
        historical_receipt_date=(
            "2099-01-01"
        ),
        historical_date_basis=(
            "OPERATOR_DECLARATION"
        ),
    )

    assert not result.is_success

    assert _events(
        repository
    ) == []


def test_quantity_must_be_strictly_positive(
    repository,
):
    _create_product(
        repository
    )

    for quantity in (
        0,
        -1,
    ):
        result = _execute(
            _use_case(repository),
            quantity=quantity,
        )

        assert not result.is_success

    assert (
        repository.get_by_id(
            "SKU-LEGACY-001"
        ).quantity
        == 0
    )

    assert _events(
        repository
    ) == []


def test_product_must_exist(
    repository,
):
    result = _execute(
        _use_case(repository)
    )

    assert not result.is_success

    assert _events(
        repository
    ) == []


def test_batch_code_is_required(
    repository,
):
    _create_product(
        repository
    )

    result = _execute(
        _use_case(repository),
        batch_code="",
    )

    assert not result.is_success

    assert (
        repository.get_by_id(
            "SKU-LEGACY-001"
        ).quantity
        == 0
    )


def test_existing_batch_cannot_be_onboarded_again(
    repository,
):
    _create_product(
        repository
    )

    first = _execute(
        _use_case(repository),
        batch_code="LEG-DUP",
        quantity=10,
    )

    assert first.is_success

    second = _execute(
        _use_case(repository),
        batch_code="LEG-DUP",
        quantity=5,
    )

    assert not second.is_success

    product = repository.get_by_id(
        "SKU-LEGACY-001"
    )

    assert product.quantity == 10

    assert (
        product.batches[
            "LEG-DUP"
        ].quantity
        == 10
    )

    assert len(
        _events(repository)
    ) == 1


def test_multiple_distinct_legacy_batches_are_supported(
    repository,
):
    _create_product(
        repository
    )

    first = _execute(
        _use_case(repository),
        batch_code="LEG-A",
        quantity=8,
        expiration_date="2026-11-10",
    )

    second = _execute(
        _use_case(repository),
        batch_code="LEG-B",
        quantity=15,
        expiration_date="2027-01-22",
    )

    assert first.is_success
    assert second.is_success

    product = repository.get_by_id(
        "SKU-LEGACY-001"
    )

    assert product.quantity == 23

    assert (
        product.batches[
            "LEG-A"
        ].quantity
        == 8
    )

    assert (
        product.batches[
            "LEG-B"
        ].quantity
        == 15
    )

    assert len(
        _events(repository)
    ) == 2


def test_known_physical_location_can_be_recorded_directly(
    repository,
):
    _create_product(
        repository
    )

    result = _execute(
        _use_case(repository),
        location_id="A-02-03",
    )

    assert result.is_success

    product = repository.get_by_id(
        "SKU-LEGACY-001"
    )

    assert (
        product.batches[
            "LEG-001"
        ].location_id
        == "A-02-03"
    )

    assert (
        _events(repository)[0][
            "location_id"
        ]
        == "A-02-03"
    )


def test_unknown_location_can_remain_pending(
    repository,
):
    _create_product(
        repository
    )

    result = _execute(
        _use_case(repository),
        location_id="",
    )

    assert result.is_success

    product = repository.get_by_id(
        "SKU-LEGACY-001"
    )

    assert (
        product.batches[
            "LEG-001"
        ].location_id
        == ""
    )


def test_supplier_and_document_are_preserved_when_known(
    repository,
):
    _create_product(
        repository
    )

    result = _execute(
        _use_case(repository),
        supplier="FORNECEDOR ANTIGO",
        document_id="NF-7788",
    )

    assert result.is_success

    event = _events(
        repository
    )[0]

    assert (
        event["supplier"]
        == "FORNECEDOR ANTIGO"
    )

    assert (
        event["document_id"]
        == "NF-7788"
    )


@pytest.mark.parametrize(
    "role",
    [
        AccessControl.ROLE_OPERATOR,
    ],
)
def test_operator_cannot_inject_existing_stock_without_management_privilege(
    repository,
    role,
):
    _create_product(
        repository
    )

    result = _execute(
        _use_case(
            repository,
            role=role,
        )
    )

    assert not result.is_success

    assert (
        repository.get_by_id(
            "SKU-LEGACY-001"
        ).quantity
        == 0
    )

    assert _events(
        repository
    ) == []


@pytest.mark.parametrize(
    "role",
    [
        AccessControl.ROLE_MANAGER,
        AccessControl.ROLE_SYSTEM_ADMIN,
        AccessControl.ROLE_SYSTEM,
    ],
)
def test_management_roles_can_onboard_existing_stock(
    repository,
    role,
):
    product_id = (
        "SKU-"
        + role.replace(
            "_",
            "-"
        )
    )

    _create_product(
        repository,
        product_id=product_id,
    )

    result = _execute(
        _use_case(
            repository,
            role=role,
        ),
        product_id=product_id,
        batch_code=(
            "LOT-"
            + role
        ),
    )

    assert result.is_success


def test_onboarding_uses_atomic_product_and_audit_writer(
    repository,
    monkeypatch,
):
    _create_product(
        repository
    )

    calls = []

    real_writer = (
        repository
        .save_product_with_operational_audit
    )

    def recording_writer(
        product,
        **event,
    ):
        calls.append(
            (
                product.id,
                event,
            )
        )

        return real_writer(
            product,
            **event,
        )

    monkeypatch.setattr(
        repository,
        "save_product_with_operational_audit",
        recording_writer,
    )

    result = _execute(
        _use_case(repository)
    )

    assert result.is_success

    assert len(calls) == 1

    assert (
        calls[0][1][
            "event_type"
        ]
        == "IMPLANTACAO_ESTOQUE"
    )


def test_atomic_failure_rolls_back_product_batch_and_event(
    repository,
    monkeypatch,
):
    _create_product(
        repository
    )

    original = (
        repository
        ._append_operational_audit_event_on_connection
    )

    def fail_for_onboarding(
        conn,
        **kwargs,
    ):
        if (
            kwargs.get(
                "event_type"
            )
            == "IMPLANTACAO_ESTOQUE"
        ):
            raise RuntimeError(
                "simulated audit failure"
            )

        return original(
            conn,
            **kwargs,
        )

    monkeypatch.setattr(
        repository,
        "_append_operational_audit_event_on_connection",
        fail_for_onboarding,
    )

    with pytest.raises(
        RuntimeError,
        match="simulated audit failure",
    ):
        _execute(
            _use_case(repository)
        )

    product = repository.get_by_id(
        "SKU-LEGACY-001"
    )

    assert product.quantity == 0

    assert (
        "LEG-001"
        not in product.batches
    )

    assert _events(
        repository
    ) == []


def test_source_does_not_delegate_to_receiving_use_case():
    path = Path(
        "src/use_cases/existing_stock_onboarding.py"
    )

    assert path.exists()

    source = path.read_text(
        encoding="utf-8"
    )

    forbidden = (
        "ReceivingUseCase",
        "RECEBIMENTO",
        "receive_stock",
    )

    for marker in forbidden:
        assert marker not in source


def test_onboarding_does_not_change_latest_receiving_semantics():
    path = Path(
        "app.py"
    )

    source = path.read_text(
        encoding="utf-8"
    )

    assert (
        "latest_receiving"
        in source
    )

    assert (
        "event_type"
        in source
    )

    region_start = source.index(
        "latest_receiving"
    )

    region = source[
        max(
            0,
            region_start - 2500,
        ):
        region_start + 2500
    ]

    assert (
        "RECEBIMENTO"
        in region
    )

    assert (
        "IMPLANTACAO_ESTOQUE"
        not in region
    )
