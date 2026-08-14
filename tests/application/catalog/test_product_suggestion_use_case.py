from src.domain.product import Product
from src.use_cases.suggest_products import ProductSuggestionUseCase


class FakeRepository:

    def __init__(self):
        self.products = [
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
                name="Bebida com Leite 200ml",
                ean="7893333333333"
            ),
            Product(
                id="SKU-004",
                name="Arroz Branco 5kg",
                ean="7894444444444"
            ),
        ]

    def get_all(self):
        return self.products


def test_product_suggestion_use_case_returns_ranked_suggestions():

    repository = FakeRepository()

    use_case = ProductSuggestionUseCase(
        repository
    )

    result = use_case.execute(
        query="leite"
    )

    assert len(result) == 3

    assert result[0].name == "Leite Integral 1L"
    assert result[1].name == "Leite Zero Lactose 1L"
    assert result[2].name == "Bebida com Leite 200ml"


def test_product_suggestion_use_case_returns_empty_for_blank_query():

    repository = FakeRepository()

    use_case = ProductSuggestionUseCase(
        repository
    )

    result = use_case.execute(
        query="   "
    )

    assert result == []


def test_product_suggestion_use_case_preserves_result_limit():

    class LargeRepository:

        def get_all(self):
            return [
                Product(
                    id=f"SKU-{index:03d}",
                    name=f"Leite Produto {index:02d}",
                    ean=f"789900000{index:04d}"
                )
                for index in range(20)
            ]

    use_case = ProductSuggestionUseCase(
        LargeRepository()
    )

    result = use_case.execute(
        query="leite"
    )

    assert len(result) == 10
