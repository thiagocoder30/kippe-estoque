from src.domain.result import Result
from src.domain.services.product_search_engine import ProductSearchEngine


class ProductQueryEngine:

    @staticmethod
    def query(
        products,
        identifier: str,
    ) -> Result[dict, str]:

        matches = ProductSearchEngine.search(
            products,
            identifier
        )

        if not matches:
            return Result.fail(
                "PRODUTO_NAO_CADASTRADO"
            )

        product = matches[0]

        batches = sorted(
            product.batches.values(),
            key=lambda batch: batch.expiration_date
        )

        return Result.ok({
            "id": product.id,
            "name": product.name,
            "ean": product.ean,
            "quantity": product.quantity,
            "batches": [
                {
                    "code": batch.code,
                    "expiration_date": batch.expiration_date,
                    "quantity": batch.quantity,
                    "location_id": batch.location_id,
                }
                for batch in batches
            ],
        })
