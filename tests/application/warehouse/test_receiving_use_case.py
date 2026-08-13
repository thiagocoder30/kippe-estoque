from src.use_cases.receive_stock import ReceivingUseCase
from src.domain.product import Product


class FakeRepository:

    def __init__(self):
        self.products = {
            "SKU-001": Product(
                id="SKU-001",
                name="Leite Integral",
                ean="7891234567890"
            )
        }
        self.saved = []

    def get_all(self):
        return list(self.products.values())

    def save(self, product):
        self.saved.append(product)


def test_receiving_use_case_receives_existing_product():

    repository = FakeRepository()

    use_case = ReceivingUseCase(repository)

    result = use_case.execute(
        identifier="7891234567890",
        quantity=15,
        batch_code="L001",
        expiration_date="2035-12-31",
        supplier="Fornecedor Teste",
    )

    assert result.is_success

    product = repository.products["SKU-001"]

    assert product.quantity == 15
    assert "L001" in product.batches
    assert len(repository.saved) == 1
