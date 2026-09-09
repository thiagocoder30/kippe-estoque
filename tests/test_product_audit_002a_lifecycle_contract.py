from copy import deepcopy
from pathlib import Path

import pytest

from src.domain.batch import Batch
from src.domain.product import Product
from src.use_cases.manage_stock import ManageStockUseCase


class FakeIdentity:
    def get_current_operator_id(self):
        return "1001"

    def get_current_operator_role(self):
        return "ADMIN_SISTEMA"


def make_product(
    *,
    quantity=20,
    batch_quantity=20,
    location_id="",
):
    product = Product(
        id="SKU-AUDIT-002",
        name="PRODUTO TESTE AUDITORIA",
        ean="7891234567890",
        quantity=quantity,
    )

    batch = Batch(
        code="LOT-AUDIT-002",
        product_id=product.id,
        quantity=batch_quantity,
        expiration_date="2027-12-31",
        supplier="FORNECEDOR TESTE",
        location_id=location_id,
    )

    product.batches[batch.code] = batch

    return product


class RepositorySpy:
    def __init__(self, product):
        self.product = product
        self.atomic_calls = []
        self.save_calls = []
        self.transaction_calls = []

    def get_by_id(self, product_id):
        if product_id == self.product.id:
            return self.product

        return None

    def save(self, product):
        self.product = product
        self.save_calls.append(product)

    def log_transaction(
        self,
        product_id,
        trans_type,
        amount,
        operator_id,
    ):
        self.transaction_calls.append(
            {
                "product_id": product_id,
                "type": trans_type,
                "amount": amount,
                "operator_id": operator_id,
            }
        )

    def save_product_with_operational_audit(
        self,
        product,
        **event,
    ):
        self.product = product
        self.atomic_calls.append(
            deepcopy(event)
        )

        return 1


class FailingAtomicRepository(RepositorySpy):
    def __init__(self, product):
        super().__init__(product)

        self.persisted_snapshot = deepcopy(
            product
        )

    def get_by_id(self, product_id):
        if product_id != self.product.id:
            return None

        # Simula entidade carregada da persistência.
        return deepcopy(
            self.persisted_snapshot
        )

    def save_product_with_operational_audit(
        self,
        product,
        **event,
    ):
        raise RuntimeError(
            "AUDIT_WRITE_FAILURE"
        )


def build_use_case(repository):
    return ManageStockUseCase(
        repository,
        identity_provider=FakeIdentity(),
    )


def test_putaway_uses_atomic_operational_audit_writer():
    repository = RepositorySpy(
        make_product()
    )

    use_case = build_use_case(
        repository
    )

    result = use_case.execute_putaway(
        "SKU-AUDIT-002",
        "LOT-AUDIT-002",
        "BOX-E2",
    )

    assert result.is_success

    assert len(
        repository.atomic_calls
    ) == 1

    event = repository.atomic_calls[0]

    assert (
        event["event_type"]
        == "PUTAWAY"
    )

    assert (
        event["product_id"]
        == "SKU-AUDIT-002"
    )

    assert (
        event["batch_code"]
        == "LOT-AUDIT-002"
    )

    assert (
        event["location_id"]
        == "BOX-E2"
    )

    assert (
        event["operator_id"]
        == "1001"
    )


def test_putaway_event_does_not_claim_quantity_movement():
    repository = RepositorySpy(
        make_product()
    )

    use_case = build_use_case(
        repository
    )

    result = use_case.execute_putaway(
        "SKU-AUDIT-002",
        "LOT-AUDIT-002",
        "BOX-E2",
    )

    assert result.is_success

    event = repository.atomic_calls[0]

    assert event["quantity_actual"] is None
    assert event["quantity_before"] == 20
    assert event["quantity_after"] == 20


def test_putaway_atomic_failure_does_not_fall_back_to_plain_save():
    repository = FailingAtomicRepository(
        make_product()
    )

    use_case = build_use_case(
        repository
    )

    with pytest.raises(
        RuntimeError,
        match="AUDIT_WRITE_FAILURE",
    ):
        use_case.execute_putaway(
            "SKU-AUDIT-002",
            "LOT-AUDIT-002",
            "BOX-E2",
        )

    assert repository.save_calls == []

    persisted = (
        repository
        .persisted_snapshot
    )

    assert (
        persisted
        .batches["LOT-AUDIT-002"]
        .location_id
        == ""
    )


def test_replenishment_uses_atomic_operational_audit_writer():
    repository = RepositorySpy(
        make_product(
            quantity=20,
            batch_quantity=20,
            location_id="BOX-E2",
        )
    )

    use_case = build_use_case(
        repository
    )

    result = (
        use_case
        .confirm_replenishment_pick(
            "SKU-AUDIT-002",
            "LOT-AUDIT-002",
            6,
        )
    )

    assert result.is_success

    assert len(
        repository.atomic_calls
    ) == 1

    event = repository.atomic_calls[0]

    assert (
        event["event_type"]
        == "ABASTECIMENTO_LOJA"
    )

    assert (
        event["product_id"]
        == "SKU-AUDIT-002"
    )

    assert (
        event["batch_code"]
        == "LOT-AUDIT-002"
    )

    assert (
        event["location_id"]
        == "BOX-E2"
    )

    assert (
        event["quantity_actual"]
        == 6
    )

    assert (
        event["quantity_before"]
        == 20
    )

    assert (
        event["quantity_after"]
        == 14
    )

    assert (
        event["operator_id"]
        == "1001"
    )


def test_replenishment_event_preserves_exact_physical_batch():
    repository = RepositorySpy(
        make_product(
            quantity=20,
            batch_quantity=20,
            location_id="BOX-E2",
        )
    )

    use_case = build_use_case(
        repository
    )

    result = (
        use_case
        .confirm_replenishment_pick(
            "SKU-AUDIT-002",
            "LOT-AUDIT-002",
            6,
        )
    )

    assert result.is_success

    event = repository.atomic_calls[0]

    assert (
        event["batch_code"]
        == result.value["batch_code"]
    )

    assert (
        event["quantity_actual"]
        == result.value[
            "confirmed_quantity"
        ]
    )


def test_replenishment_atomic_failure_does_not_persist_stock_mutation():
    repository = FailingAtomicRepository(
        make_product(
            quantity=20,
            batch_quantity=20,
            location_id="BOX-E2",
        )
    )

    use_case = build_use_case(
        repository
    )

    with pytest.raises(
        RuntimeError,
        match="AUDIT_WRITE_FAILURE",
    ):
        use_case.confirm_replenishment_pick(
            "SKU-AUDIT-002",
            "LOT-AUDIT-002",
            6,
        )

    assert repository.save_calls == []

    persisted = (
        repository
        .persisted_snapshot
    )

    assert persisted.quantity == 20

    assert (
        persisted
        .batches["LOT-AUDIT-002"]
        .quantity
        == 20
    )


def test_lifecycle_audit_keeps_product_batch_as_stock_authority():
    source = Path(
        "src/interfaces/sqlite_repository.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "Nenhum saldo é calculado "
        "a partir desta tabela."
        in source
    )

    assert (
        "save_product_with_operational_audit"
        in source
    )
