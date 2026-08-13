from src.use_cases.query_product import ProductQueryUseCase
from src.domain.product import Product


class FakeRepository:

    def __init__(self):
        self.products = [
            Product(
                id="SKU-001",
                name="Leite Integral",
                ean="7891234567890"
            )
        ]

    def get_all(self):
        return self.products


def test_product_query_use_case_returns_product_view():

    repository = FakeRepository()

    use_case = ProductQueryUseCase(repository)

    result = use_case.execute(
        identifier="7891234567890"
    )

    assert result.is_success

    data = result.value

    assert data["id"] == "SKU-001"
    assert data["name"] == "Leite Integral"


def test_product_query_use_case_returns_not_found():

    repository = FakeRepository()

    use_case = ProductQueryUseCase(repository)

    result = use_case.execute(
        identifier="7890000000000"
    )

    assert not result.is_success
    assert result.error == "PRODUTO_NAO_CADASTRADO"


def test_product_query_use_case_returns_expiration_intelligence():

    product = Product(
        id="SKU-FEFO-APP",
        name="Produto FEFO",
        ean="7895555555555"
    )

    product.add_stock(
        amount=10,
        expiration_date="2026-09-01",
        batch_code="L001"
    )

    class FEFORepository:
        def get_all(self):
            return [product]

    use_case = ProductQueryUseCase(
        FEFORepository()
    )

    result = use_case.execute(
        identifier="7895555555555"
    )

    assert result.is_success

    batch = result.value["batches"][0]

    assert batch["code"] == "L001"
    assert batch["expiration_status"] == "ATENCAO"
