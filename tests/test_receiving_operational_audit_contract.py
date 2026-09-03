from src.domain.product import Product
from src.use_cases.receive_stock import ReceivingUseCase


class AuditAwareFakeRepository:

    def __init__(self):
        self.products = {
            "SKU-001": Product(
                id="SKU-001",
                name="LEITE INTEGRAL TESTE",
                ean="7891234567890",
            )
        }

        self.saved = []
        self.audit_events = []

    def get_all(self):
        return list(
            self.products.values()
        )

    def save(self, product):
        self.saved.append(
            product
        )

    def append_operational_audit_event(
        self,
        **event,
    ):
        self.audit_events.append(
            dict(event)
        )

        return len(
            self.audit_events
        )


def _execute_receiving(
    repository,
    *,
    quantity=15,
    batch_code="L001",
    supplier="FORNECEDOR TESTE",
    invoice_id="NF-001",
    origin_document="MANUAL",
    operator_id="OP-001",
):
    use_case = ReceivingUseCase(
        repository
    )

    return use_case.execute(
        identifier="7891234567890",
        quantity=quantity,
        batch_code=batch_code,
        expiration_date="2035-12-31",
        supplier=supplier,
        manufacturing_date="2035-01-01",
        invoice_id=invoice_id,
        origin_document=origin_document,
        operator_id=operator_id,
    )


def test_successful_receiving_appends_one_documentary_event():
    repository = (
        AuditAwareFakeRepository()
    )

    result = _execute_receiving(
        repository
    )

    assert result.is_success

    assert len(
        repository.saved
    ) == 1

    assert len(
        repository.audit_events
    ) == 1


def test_receiving_audit_event_has_canonical_event_type_and_product():
    repository = (
        AuditAwareFakeRepository()
    )

    result = _execute_receiving(
        repository
    )

    assert result.is_success

    event = (
        repository.audit_events[0]
    )

    assert (
        event["event_type"]
        == "RECEBIMENTO"
    )

    assert (
        event["product_id"]
        == "SKU-001"
    )

    assert (
        event["batch_code"]
        == "L001"
    )


def test_receiving_audit_records_actual_quantity_and_product_balance():
    repository = (
        AuditAwareFakeRepository()
    )

    product = (
        repository.products[
            "SKU-001"
        ]
    )

    assert product.quantity == 0

    result = _execute_receiving(
        repository,
        quantity=15,
    )

    assert result.is_success
    assert product.quantity == 15

    event = (
        repository.audit_events[0]
    )

    assert (
        event["quantity_actual"]
        == 15
    )

    assert (
        event["quantity_before"]
        == 0
    )

    assert (
        event["quantity_after"]
        == 15
    )

    assert (
        event["quantity_planned"]
        is None
    )

    assert (
        event["quantity_divergence"]
        is None
    )


def test_receiving_existing_stock_records_real_before_and_after_balance():
    repository = (
        AuditAwareFakeRepository()
    )

    product = (
        repository.products[
            "SKU-001"
        ]
    )

    seed = product.add_stock(
        amount=8,
        expiration_date=(
            "2035-12-31"
        ),
        batch_code="L001",
        manufacturing_date=(
            "2035-01-01"
        ),
        supplier=(
            "FORNECEDOR TESTE"
        ),
    )

    assert seed.is_success
    assert product.quantity == 8

    result = _execute_receiving(
        repository,
        quantity=7,
        batch_code="L001",
    )

    assert result.is_success
    assert product.quantity == 15

    event = (
        repository.audit_events[0]
    )

    assert (
        event["quantity_actual"]
        == 7
    )

    assert (
        event["quantity_before"]
        == 8
    )

    assert (
        event["quantity_after"]
        == 15
    )


def test_receiving_audit_preserves_supplier_and_document_traceability():
    repository = (
        AuditAwareFakeRepository()
    )

    result = _execute_receiving(
        repository,
        supplier=(
            "DISTRIBUIDORA TESTE"
        ),
        invoice_id="NF-987",
        origin_document="XML",
    )

    assert result.is_success

    event = (
        repository.audit_events[0]
    )

    assert (
        event["supplier"]
        == "DISTRIBUIDORA TESTE"
    )

    assert (
        event["document_id"]
        == "NF-987"
    )

    assert (
        event["origin_document"]
        == "XML"
    )


def test_receiving_audit_preserves_operator_identity():
    repository = (
        AuditAwareFakeRepository()
    )

    result = _execute_receiving(
        repository,
        operator_id="1001",
    )

    assert result.is_success

    event = (
        repository.audit_events[0]
    )

    assert (
        event["operator_id"]
        == "1001"
    )


def test_receiving_documentary_metadata_preserves_dates():
    repository = (
        AuditAwareFakeRepository()
    )

    result = _execute_receiving(
        repository
    )

    assert result.is_success

    event = (
        repository.audit_events[0]
    )

    metadata = (
        event["metadata"]
    )

    assert (
        metadata[
            "manufacturing_date"
        ]
        == "2035-01-01"
    )

    assert (
        metadata[
            "expiration_date"
        ]
        == "2035-12-31"
    )


def test_failed_receiving_does_not_append_documentary_event():
    repository = (
        AuditAwareFakeRepository()
    )

    use_case = ReceivingUseCase(
        repository
    )

    result = use_case.execute(
        identifier=(
            "EAN-NAO-CADASTRADO"
        ),
        quantity=10,
        batch_code="L-FAIL",
        expiration_date=(
            "2035-12-31"
        ),
        supplier=(
            "FORNECEDOR TESTE"
        ),
        manufacturing_date=(
            "2035-01-01"
        ),
        invoice_id="NF-FAIL",
        origin_document="MANUAL",
        operator_id="OP-FAIL",
    )

    assert not result.is_success

    assert repository.saved == []

    assert (
        repository.audit_events
        == []
    )


def test_invalid_receiving_quantity_does_not_append_documentary_event():
    repository = (
        AuditAwareFakeRepository()
    )

    result = _execute_receiving(
        repository,
        quantity=0,
    )

    assert not result.is_success

    assert (
        repository.audit_events
        == []
    )


def test_receiving_event_does_not_create_second_stock_mutation():
    repository = (
        AuditAwareFakeRepository()
    )

    product = (
        repository.products[
            "SKU-001"
        ]
    )

    result = _execute_receiving(
        repository,
        quantity=11,
    )

    assert result.is_success

    assert product.quantity == 11

    assert len(
        repository.audit_events
    ) == 1

    # A evidência documental registra 11,
    # mas não pode aplicar outros 11.
    assert product.quantity == 11


def test_receiving_result_remains_backward_compatible():
    repository = (
        AuditAwareFakeRepository()
    )

    result = _execute_receiving(
        repository,
        quantity=6,
    )

    assert result.is_success

    assert (
        result.value["status"]
        == "RECEIVED"
    )

    assert (
        result.value["product_id"]
        == "SKU-001"
    )

    assert (
        result.value["batch_code"]
        == "L001"
    )

    assert (
        result.value["quantity"]
        == 6
    )
