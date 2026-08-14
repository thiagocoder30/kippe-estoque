from typing import Iterable, List

from src.domain.product import Product
from src.domain.services.product_search_engine import ProductSearchEngine


class ProductSuggestionEngine:

    MAX_SUGGESTIONS = 10

    @staticmethod
    def suggest(
        products: Iterable[Product],
        query: str,
    ) -> List[Product]:

        if not query or not query.strip():
            return []

        normalized_query = query.strip().lower()

        matches = ProductSearchEngine.search(
            products,
            normalized_query
        )

        ranked = sorted(
            matches,
            key=lambda product: (
                not product.name.lower().startswith(normalized_query),
                product.name.lower(),
            ),
        )

        return ranked[:ProductSuggestionEngine.MAX_SUGGESTIONS]
