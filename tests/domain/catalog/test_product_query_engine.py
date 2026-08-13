from src.domain.services.product_query_engine import ProductQueryEngine
from src.domain.product import Product


def test_query_product_returns_operational_view():

    product = Product(
        id="SKU-001",
        name="Leite Integral 1L",
        ean="7891234567890"
    )

    product.add_stock(
        amount=50,
        expiration_date="2035-12-31",
        batch_code="L001"
    )

    result = ProductQueryEngine.query(
        products=[product],
        identifier="7891234567890"
    )

    assert result.is_success

    data = result.value

    assert data["id"] == "SKU-001"
    assert data["name"] == "Leite Integral 1L"
    assert data["quantity"] == 50
    assert len(data["batches"]) == 1
    assert data["batches"][0]["code"] == "L001"


def test_query_unknown_product_returns_not_found():

    result = ProductQueryEngine.query(
        products=[],
        identifier="7890000000000"
    )

    assert not result.is_success
    assert result.error == "PRODUTO_NAO_CADASTRADO"


def test_query_returns_batches_in_fefo_order():

    product = Product(
        id="SKU-FEFO",
        name="Produto FEFO",
        ean="7895555555555"
    )

    product.add_stock(
        amount=10,
        expiration_date="2030-12-31",
        batch_code="L001"
    )

    product.add_stock(
        amount=5,
        expiration_date="2027-01-01",
        batch_code="L002"
    )

    result = ProductQueryEngine.query(
        products=[product],
        identifier="7895555555555"
    )

    assert result.is_success

    batches = result.value["batches"]

    assert batches[0]["code"] == "L002"
    assert batches[1]["code"] == "L001"


def test_query_returns_expiration_status_for_batches():

    product = Product(
        id="SKU-EXP",
        name="Produto Validade",
        ean="7896666666666"
    )

    product.add_stock(
        amount=10,
        expiration_date="2026-09-01",
        batch_code="L-EXP"
    )

    result = ProductQueryEngine.query(
        products=[product],
        identifier="7896666666666"
    )

    assert result.is_success

    batch = result.value["batches"][0]

    assert batch["code"] == "L-EXP"
    assert batch["expiration_status"] == "ATENCAO"
    assert batch["days_remaining"] > 0
