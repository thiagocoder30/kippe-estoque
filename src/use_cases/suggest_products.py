from typing import List

from src.domain.product import Product
from src.domain.services.product_suggestion_engine import ProductSuggestionEngine


class ProductSuggestionUseCase:

    def __init__(self, repository):
        self.repository = repository

    def execute(
        self,
        query: str,
    ) -> List[Product]:

        products = self.repository.get_all()

        return ProductSuggestionEngine.suggest(
            products=products,
            query=query,
        )
