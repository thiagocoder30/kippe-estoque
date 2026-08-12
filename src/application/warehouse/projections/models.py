from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class GlobalInventoryProjection:
    total_skus: int
    total_items: int
    estimated_value: float
    critical_skus_count: int
    avg_trust_score: float
    top_critical_skus: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ExpirationProjection:
    expiring_in_7_days: List[Dict[str, Any]] = field(default_factory=list)
    expiring_in_15_days: List[Dict[str, Any]] = field(default_factory=list)
    expiring_in_30_days: List[Dict[str, Any]] = field(default_factory=list)
    already_expired: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class PurchaseProjection:
    urgent_replenishment: List[Dict[str, Any]] = field(default_factory=list)
    planned_replenishment: List[Dict[str, Any]] = field(default_factory=list)
