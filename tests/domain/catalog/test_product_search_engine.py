from src.domain.product import Product
from src.domain.services.product_search_engine import ProductSearchEngine


def test_search_product_by_ean():

    products = [
        Product(
            id="SKU-001",
            name="Leite Integral 1L",
            ean="7891234567890"
        ),
        Product(
            id="SKU-002",
            name="Arroz 5kg",
            ean="7899999999999"
        ),
    ]

    result = ProductSearchEngine.search(
        products,
        "7891234567890"
    )

    assert len(result) == 1
    assert result[0].id == "SKU-001"


def test_search_product_by_description_partial():

    products = [
        Product(
            id="SKU-003",
            name="Leite Integral 1L",
            ean="7891111111111"
        ),
        Product(
            id="SKU-004",
            name="Feijão 1kg",
            ean="7892222222222"
        ),
    ]

    result = ProductSearchEngine.search(
        products,
        "leite"
    )

    assert len(result) == 1
    assert result[0].name == "Leite Integral 1L"


def test_search_returns_empty_when_not_found():

    products = [
        Product(
            id="SKU-005",
            name="Cafe 500g",
            ean="7893333333333"
        )
    ]

    result = ProductSearchEngine.search(
        products,
        "arroz"
    )

    assert result == []
