from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass(frozen=True)
class SKUOperationalSnapshot:
    sku: str

    # estoque
    stock_total: int

    # estrutura física
    batches: List[Dict[str, Any]]
    first_expiration_date: str
    supplier: str

    # inteligência operacional
    trust_score: float
    divergence_penalty: float
    risk_score: float

    # decisão
    priority: str
    suggested_action: str

    # recomendação de compra
    replenishment_quantity: int


class SKUOperationalSnapshotBuilder:

    @staticmethod
    def build(
        sku: str,
        account,
        sheet,
        dual_stock: Dict[str, Any],
        trust,
        divergence_events,
        replenishment,
        operational_insight
    ) -> SKUOperationalSnapshot:

        # -----------------------------
        # BATCHES (fonte: sheet)
        # -----------------------------
        batches = sheet.batches if hasattr(sheet, "batches") else []

        # -----------------------------
        # EXPIRAÇÃO
        # -----------------------------
        first_expiration = (
            sheet.next_to_expire.get("expiration", "N/A")
            if hasattr(sheet, "next_to_expire")
            else "N/A"
        )

        # -----------------------------
        # SUPPLIER (heurística simples institucional)
        # -----------------------------
        supplier = "UNKNOWN"
        if batches and isinstance(batches, list):
            suppliers = [
                b.get("supplier")
                for b in batches
                if isinstance(b, dict) and b.get("supplier")
            ]
            supplier = suppliers[0] if suppliers else "UNKNOWN"

        # -----------------------------
        # STOCK
        # -----------------------------
        stock_total = dual_stock.get("total", 0)

        # -----------------------------
        # RISK
        # -----------------------------
        risk_score = (
            divergence_events.risk_score if hasattr(divergence_events, "risk_score") else 0.0
        )

        trust_score = getattr(trust, "score", 1.0)
        divergence_penalty = 1.0 - trust_score

        # -----------------------------
        # REPLENISHMENT
        # -----------------------------
        replenishment_qty = (
            getattr(replenishment, "quantity", None)
            or getattr(replenishment, "recommended_quantity", None)
            or 0
        )

        # -----------------------------
        # INSIGHT (decisão institucional)
        # -----------------------------
        priority = getattr(operational_insight.priority, "value", str(operational_insight.priority))
        suggested_action = operational_insight.suggested_action

        return SKUOperationalSnapshot(
            sku=sku,
            stock_total=stock_total,
            batches=batches,
            first_expiration_date=first_expiration,
            supplier=supplier,
            trust_score=trust_score,
            divergence_penalty=divergence_penalty,
            risk_score=risk_score,
            priority=priority,
            suggested_action=suggested_action,
            replenishment_quantity=replenishment_qty
        )
