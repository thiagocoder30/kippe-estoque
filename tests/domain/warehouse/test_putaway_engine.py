from src.domain.services.putaway_engine import PutawayEngine
from src.domain.product import Product


def test_putaway_updates_batch_location():

    product = Product(
        id="SKU-001",
        name="Produto Teste"
    )

    product.add_stock(
        amount=10,
        expiration_date="2035-12-31",
        batch_code="L001"
    )

    result = PutawayEngine.execute_putaway(
        product,
        "L001",
        "EST-A-01"
    )

    assert result.is_success
    assert product.batches["L001"].location_id == "EST-A-01"


def test_putaway_fails_when_batch_not_found():

    product = Product(
        id="SKU-002",
        name="Produto Teste"
    )

    result = PutawayEngine.execute_putaway(
        product,
        "LOTE-INEXISTENTE",
        "EST-A-01"
    )

    assert not result.is_success
    assert "Lote não encontrado" in result.error


def test_putaway_fails_without_location():

    product = Product(
        id="SKU-003",
        name="Produto Teste"
    )

    product.add_stock(
        amount=5,
        expiration_date="2035-12-31",
        batch_code="L003"
    )

    result = PutawayEngine.execute_putaway(
        product,
        "L003",
        ""
    )

    assert not result.is_success
    assert "Localização obrigatória" in result.error
