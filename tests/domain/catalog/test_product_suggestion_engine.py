from src.domain.product import Product
from src.domain.services.product_suggestion_engine import ProductSuggestionEngine


def test_product_suggestion_engine_returns_description_matches():

    products = [
        Product(
            id="SKU-001",
            name="Leite Integral 1L",
            ean="7891111111111"
        ),
        Product(
            id="SKU-002",
            name="Leite Zero Lactose 1L",
            ean="7892222222222"
        ),
        Product(
            id="SKU-003",
            name="Arroz Branco 5kg",
            ean="7893333333333"
        ),
    ]

    result = ProductSuggestionEngine.suggest(
        products=products,
        query="leite"
    )

    assert len(result) == 2

    names = [product.name for product in result]

    assert "Leite Integral 1L" in names
    assert "Leite Zero Lactose 1L" in names


def test_product_suggestion_engine_prioritizes_names_starting_with_query():

    products = [
        Product(
            id="SKU-010",
            name="Bebida com Leite 200ml",
            ean="7894444444444"
        ),
        Product(
            id="SKU-011",
            name="Leite Integral 1L",
            ean="7895555555555"
        ),
        Product(
            id="SKU-012",
            name="Leite Zero Lactose 1L",
            ean="7896666666666"
        ),
    ]

    result = ProductSuggestionEngine.suggest(
        products=products,
        query="leite"
    )

    assert len(result) == 3
    assert result[0].name == "Leite Integral 1L"
    assert result[1].name == "Leite Zero Lactose 1L"
    assert result[2].name == "Bebida com Leite 200ml"


def test_product_suggestion_engine_returns_empty_for_blank_query():

    products = [
        Product(
            id="SKU-020",
            name="Leite Integral 1L",
            ean="7897777777777"
        ),
        Product(
            id="SKU-021",
            name="Arroz Branco 5kg",
            ean="7898888888888"
        ),
    ]

    result = ProductSuggestionEngine.suggest(
        products=products,
        query="   "
    )

    assert result == []


def test_product_suggestion_engine_limits_results():

    products = [
        Product(
            id=f"SKU-{index:03d}",
            name=f"Leite Produto {index:02d}",
            ean=f"789900000{index:04d}"
        )
        for index in range(20)
    ]

    result = ProductSuggestionEngine.suggest(
        products=products,
        query="leite"
    )

    assert len(result) == 10
