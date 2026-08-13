from typing import Iterable, List

from src.domain.product import Product


class ProductSearchEngine:

    @staticmethod
    def search(
        products: Iterable[Product],
        query: str
    ) -> List[Product]:

        if not query:
            return []

        result = []

        for product in products:
            if product.matches_identifier(query):
                result.append(product)

        return result
