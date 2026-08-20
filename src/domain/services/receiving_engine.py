from src.domain.result import Result
from src.domain.services.product_search_engine import ProductSearchEngine


class ReceivingEngine:

    @staticmethod
    def receive(
        products,
        identifier: str,
        quantity: int,
        batch_code: str,
        expiration_date: str,
        supplier: str = "PADRAO",
        manufacturing_date: str = "",
    ) -> Result[dict, str]:

        matches = ProductSearchEngine.search(
            products,
            identifier,
        )

        if not matches:
            return Result.fail(
                "PRODUTO_NAO_CADASTRADO"
            )

        product = matches[0]

        result = product.add_stock(
            amount=quantity,
            expiration_date=expiration_date,
            batch_code=batch_code,
            manufacturing_date=manufacturing_date,
            supplier=supplier,
        )

        if not result.is_success:
            return Result.fail(result.error)

        return Result.ok({
            "status": "RECEIVED",
            "product_id": product.id,
            "batch_code": batch_code,
            "quantity": quantity,
            "supplier": supplier,
            "manufacturing_date": manufacturing_date,
            "expiration_date": expiration_date,
        })
