from src.domain.result import Result
from src.domain.services.product_search_engine import ProductSearchEngine
from src.domain.services.expiration_analyzer import ExpirationAnalyzer


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

        batches = []

        for batch in sorted(
            product.batches.values(),
            key=lambda batch: batch.expiration_date
        ):
            expiration = ExpirationAnalyzer.analyze(
                batch.expiration_date
            )

            batch_data = {
                "code": batch.code,
                "expiration_date": batch.expiration_date,
                "quantity": batch.quantity,
                "location_id": batch.location_id,
            }

            if expiration.is_success:
                batch_data.update({
                    "expiration_status": expiration.value["status"],
                    "days_remaining": expiration.value["days_remaining"],
                })

            batches.append(batch_data)

        return Result.ok({
            "id": product.id,
            "name": product.name,
            "ean": product.ean,
            "quantity": product.quantity,
            "batches": batches,
        })
