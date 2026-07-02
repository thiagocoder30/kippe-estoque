from typing import Any
from src.application.warehouse.snapshot.sku_snapshot_model import (
    SKUSnapshot, StockSnapshot, BatchSnapshot, RiskSnapshot, ReplenishmentSnapshot
)
from src.domain.warehouse.smart_sheet import SmartSheetBuilder
from src.domain.warehouse.movement import DualStockView
from src.domain.warehouse.replenishment import ReplenishmentEngine
from src.domain.warehouse.operational_truth import OperationalTruthEngine


class SKUSnapshotBuilder:

    @staticmethod
    def build(account: Any, sku: str, min_stock: int = 40, ideal_stock: int = 120) -> SKUSnapshot:
        try:
            sheet = SmartSheetBuilder.build(account)
        except Exception:
            class FakeSheet:
                batches = []
            sheet = FakeSheet()

        try:
            dual_stock = DualStockView.calculate(account.entries, sku)
        except Exception:
            dual_stock = {"total": 0, "depot": 0, "store": 0}

        trust_score = 1.0

        try:
            replenishment = ReplenishmentEngine.calculate(sheet, min_stock, ideal_stock)
        except Exception:
            replenishment = None
            
        try:
            insight = OperationalTruthEngine.evaluate(
                sku=sku,
                stock_total=dual_stock["total"],
                divergence_penalty=0.0,
                trust_score=trust_score,
                inbound_risk=0.0
            )
        except Exception:
            class FakeInsight:
                priority = "NORMAL"
            insight = FakeInsight()

        batches = []
        for b in getattr(sheet, "batches", []):
            try:
                batches.append(
                    BatchSnapshot(
                        batch_code=b.get("id", "UNKNOWN"),
                        quantity=b.get("qty", 0),
                        expiration_date=b.get("expiration", "9999-12-31"),
                        supplier=b.get("supplier", "UNKNOWN")
                    )
                )
            except Exception:
                pass

        stock = StockSnapshot(
            total_qty=dual_stock["total"],
            available_qty=dual_stock["total"],
            by_batch=batches
        )

        priority_val = getattr(insight, "priority", "NORMAL")
        if hasattr(priority_val, "value"):
            priority_val = priority_val.value

        risk = RiskSnapshot(
            divergence_score=0.0,
            trust_score=trust_score,
            inbound_risk=0.0,
            priority=str(priority_val)
        )

        sugg_qty = getattr(replenishment, "suggested_quantity", getattr(replenishment, "quantity", 0)) if replenishment else 0
        needs_restock = getattr(replenishment, "needs_replenishment", sugg_qty > 0) if replenishment else False

        replenishment_snapshot = ReplenishmentSnapshot(
            needs_restock=needs_restock,
            suggested_order_qty=sugg_qty,
            min_stock=min_stock,
            ideal_stock=ideal_stock,
            reasoning=getattr(replenishment, "reason", "OK") if replenishment else "OK"
        )

        return SKUSnapshot(
            sku=sku,
            stock=stock,
            risk=risk,
            replenishment=replenishment_snapshot,
            last_movement=None,
            last_adjustment=None
        )

