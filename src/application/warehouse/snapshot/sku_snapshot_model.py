from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass(frozen=True)
class BatchSnapshot:
    batch_code: str
    quantity: int
    expiration_date: str
    supplier: str


@dataclass(frozen=True)
class RiskSnapshot:
    divergence_score: float
    trust_score: float
    inbound_risk: float
    priority: str


@dataclass(frozen=True)
class StockSnapshot:
    total_qty: int
    available_qty: int
    by_batch: List[BatchSnapshot]


@dataclass(frozen=True)
class ReplenishmentSnapshot:
    needs_restock: bool
    suggested_order_qty: int
    min_stock: int
    ideal_stock: int
    reasoning: str


@dataclass(frozen=True)
class SKUSnapshot:
    sku: str
    stock: StockSnapshot
    risk: RiskSnapshot
    replenishment: ReplenishmentSnapshot
    last_movement: Optional[str] = None
    last_adjustment: Optional[str] = None
