from src.domain.result import Result
from src.domain.services.product_query_engine import ProductQueryEngine


class ProductQueryUseCase:

    def __init__(self, repository):
        self.repository = repository

    def execute(
        self,
        identifier: str,
    ) -> Result[dict, str]:

        products = self.repository.get_all()

        return ProductQueryEngine.query(
            products=products,
            identifier=identifier,
        )
