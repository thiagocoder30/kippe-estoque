from src.domain.result import Result
from src.domain.services.receiving_engine import ReceivingEngine


class ReceivingUseCase:

    def __init__(self, repository):
        self.repository = repository

    def execute(
        self,
        identifier: str,
        quantity: int,
        batch_code: str,
        expiration_date: str,
        supplier: str = "PADRAO",
    ) -> Result[dict, str]:

        products = self.repository.get_all()

        result = ReceivingEngine.receive(
            products=products,
            identifier=identifier,
            quantity=quantity,
            batch_code=batch_code,
            expiration_date=expiration_date,
            supplier=supplier,
        )

        if not result.is_success:
            return result

        product_id = result.value["product_id"]

        product = next(
            (
                product
                for product in products
                if product.id == product_id
            ),
            None,
        )

        if product:
            self.repository.save(product)

        return result
