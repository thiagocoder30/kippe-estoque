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
        manufacturing_date: str = "",
        invoice_id: str = "",
        origin_document: str = "MANUAL",
        operator_id: str = "SYSTEM",
    ) -> Result[dict, str]:

        products = self.repository.get_all()

        quantity_before_by_product = {
            product.id: product.quantity
            for product in products
        }

        result = ReceivingEngine.receive(
            products=products,
            identifier=identifier,
            quantity=quantity,
            batch_code=batch_code,
            expiration_date=expiration_date,
            supplier=supplier,
            manufacturing_date=manufacturing_date,
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
            quantity_before = (
                quantity_before_by_product[
                    product_id
                ]
            )

            audit_event = {
                "event_type": "RECEBIMENTO",
                "product_id": product_id,
                "batch_code": result.value[
                    "batch_code"
                ],
                "location_id": "",
                "quantity_planned": None,
                "quantity_actual": result.value[
                    "quantity"
                ],
                "quantity_before": quantity_before,
                "quantity_after": product.quantity,
                "quantity_divergence": None,
                "supplier": result.value[
                    "supplier"
                ],
                "document_id": invoice_id,
                "origin_document": origin_document,
                "operator_id": operator_id,
                "metadata": {
                    "manufacturing_date": (
                        result.value[
                            "manufacturing_date"
                        ]
                    ),
                    "expiration_date": (
                        result.value[
                            "expiration_date"
                        ]
                    ),
                },
            }

            atomic_writer = getattr(
                self.repository,
                "save_product_with_operational_audit",
                None,
            )

            if callable(atomic_writer):
                atomic_writer(
                    product,
                    **audit_event,
                )
            else:
                self.repository.save(
                    product
                )

                audit_writer = getattr(
                    self.repository,
                    "append_operational_audit_event",
                    None,
                )

                if callable(audit_writer):
                    audit_writer(
                        **audit_event
                    )

        return result
