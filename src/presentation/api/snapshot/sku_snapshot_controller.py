from typing import Any


class SKUSnapshotController:

    def __init__(self, snapshot_service):
        self.snapshot_service = snapshot_service

    def get_sku_snapshot(self, sku: str):
        try:
            snapshot = self.snapshot_service.get_snapshot(sku)

            return 200, {
                "sku": snapshot.sku,
                "stock": {
                    "total_qty": snapshot.stock.total_qty,
                    "available_qty": snapshot.stock.available_qty,
                    "batches": [
                        {
                            "batch_code": b.batch_code,
                            "quantity": b.quantity,
                            "expiration_date": b.expiration_date,
                            "supplier": b.supplier
                        }
                        for b in snapshot.stock.by_batch
                    ]
                },
                "risk": {
                    "divergence_score": snapshot.risk.divergence_score,
                    "trust_score": snapshot.risk.trust_score,
                    "inbound_risk": snapshot.risk.inbound_risk,
                    "priority": snapshot.risk.priority
                },
                "replenishment": {
                    "needs_restock": snapshot.replenishment.needs_restock,
                    "suggested_order_qty": snapshot.replenishment.suggested_order_qty,
                    "min_stock": snapshot.replenishment.min_stock,
                    "ideal_stock": snapshot.replenishment.ideal_stock,
                    "reasoning": snapshot.replenishment.reasoning
                }
            }

        except Exception as e:
            return 500, {"error": str(e)}
