from src.domain.services.receiving_engine import ReceivingEngine
from src.domain.product import Product


def test_receiving_existing_product_creates_stock():

    product = Product(
        id="SKU-001",
        name="Leite Integral 1L",
        ean="7891234567890"
    )

    result = ReceivingEngine.receive(
        products=[product],
        identifier="7891234567890",
        quantity=20,
        batch_code="L001",
        expiration_date="2035-12-31",
        supplier="Fornecedor Teste",
    )

    assert result.is_success

    assert product.quantity == 20
    assert "L001" in product.batches
    assert product.batches["L001"].supplier == "Fornecedor Teste"


def test_receiving_unknown_product_requires_registration():

    result = ReceivingEngine.receive(
        products=[],
        identifier="7890000000000",
        quantity=10,
        batch_code="NOVO001",
        expiration_date="2035-12-31",
        supplier="Fornecedor Novo",
    )

    assert not result.is_success
    assert result.error == "PRODUTO_NAO_CADASTRADO"


def test_receiving_blocks_invalid_quantity():

    product = Product(
        id="SKU-002",
        name="Arroz 5kg",
        ean="7899999999999"
    )

    result = ReceivingEngine.receive(
        products=[product],
        identifier="7899999999999",
        quantity=0,
        batch_code="L002",
        expiration_date="2035-12-31",
        supplier="Fornecedor Teste",
    )

    assert not result.is_success
    assert "Quantidade" in result.error


def test_receiving_blocks_invalid_expiration_date():

    product = Product(
        id="SKU-003",
        name="Produto Validade",
        ean="7898888888888"
    )

    result = ReceivingEngine.receive(
        products=[product],
        identifier="7898888888888",
        quantity=10,
        batch_code="L003",
        expiration_date="31-12-2035",
        supplier="Fornecedor Teste",
    )

    assert not result.is_success
    assert "Formato de data inválido" in result.error


def test_receiving_existing_batch_accumulates_quantity():

    product = Product(
        id="SKU-004",
        name="Leite Integral",
        ean="7897777777777"
    )

    first = ReceivingEngine.receive(
        products=[product],
        identifier="7897777777777",
        quantity=20,
        batch_code="L001",
        expiration_date="2035-12-31",
        supplier="Fornecedor Teste",
    )

    second = ReceivingEngine.receive(
        products=[product],
        identifier="7897777777777",
        quantity=10,
        batch_code="L001",
        expiration_date="2035-12-31",
        supplier="Fornecedor Teste",
    )

    assert first.is_success
    assert second.is_success

    assert product.quantity == 30
    assert product.batches["L001"].quantity == 30
