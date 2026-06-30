from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, List, Any

DivergenceType = Literal[
    "THEFT_SUSPECTED",
    "UNREGISTERED_WITHDRAWAL",
    "PHYSICAL_COUNT_CORRECTION",
    "SYSTEM_ERROR",
    "EXPIRED_LOSS"
]

@dataclass(frozen=True)
class DivergenceEvent:
    sku: str
    system_quantity: int
    physical_quantity: int
    delta: int
    divergence_type: DivergenceType
    reason: Optional[str]
    created_at: str

@dataclass(frozen=True)
class TrustScore:
    sku: str
    score: float
    divergence_count: int
    total_adjustment_volume: int
    risk_level: str

@dataclass(frozen=True)
class InventoryRealitySnapshot:
    sku: str
    system_quantity: int
    physical_quantity: int
    divergence: int
    trust_score: float
    last_updated: str

class DivergenceEngine:
    @staticmethod
    def evaluate(sku: str, system_quantity: int, physical_quantity: int, reason: Optional[str] = None) -> Optional[DivergenceEvent]:
        delta = physical_quantity - system_quantity
        if delta == 0:
            return None

        divergence_type = DivergenceEngine._classify(delta, reason)
        return DivergenceEvent(
            sku=sku, system_quantity=system_quantity, physical_quantity=physical_quantity,
            delta=delta, divergence_type=divergence_type, reason=reason,
            created_at=datetime.now().isoformat()
        )

    @staticmethod
    def _classify(delta: int, reason: Optional[str]) -> DivergenceType:
        if reason and "venc" in reason.lower(): return "EXPIRED_LOSS"
        if delta < 0: return "UNREGISTERED_WITHDRAWAL"
        if delta > 0: return "PHYSICAL_COUNT_CORRECTION"
        return "SYSTEM_ERROR"

    @staticmethod
    def extract_from_ledger(entries: List[Any]) -> List[DivergenceEvent]:
        """
        Fábrica de Reconstrução: Lê a Fonte da Verdade (Ledger) e materializa os eventos de divergência.
        Blinda a Camada de Aplicação contra os detalhes estruturais do Ledger.
        """
        events = []
        for e in entries:
            if e.transaction_type.name == "ADJUSTMENT" and "div_type" in e.metadata:
                events.append(DivergenceEvent(
                    sku=e.sku,
                    system_quantity=0,
                    physical_quantity=0,
                    delta=e.quantity,
                    divergence_type=e.metadata.get("div_type", "SYSTEM_ERROR"),
                    reason=e.metadata.get("reason"),
                    created_at=e.timestamp
                ))
        return events

class TrustScoreEngine:
    @staticmethod
    def calculate(events: List[DivergenceEvent]) -> TrustScore:
        if not events:
            return TrustScore(sku="UNKNOWN", score=1.0, divergence_count=0, total_adjustment_volume=0, risk_level="LOW")

        total_delta = sum(abs(e.delta) for e in events)
        count = len(events)
        score = 1.0 - min(0.5, count * 0.05) - min(0.5, total_delta * 0.01)
        score = max(0.0, score)

        if score >= 0.8: risk = "LOW"
        elif score >= 0.5: risk = "MEDIUM"
        elif score >= 0.2: risk = "HIGH"
        else: risk = "CRITICAL"

        return TrustScore(sku=events[0].sku, score=round(score, 2), divergence_count=count, total_adjustment_volume=total_delta, risk_level=risk)

class InventoryRealityEngine:
    @staticmethod
    def build_snapshot(sku: str, system_qty: int, physical_qty: int, trust_score: float) -> InventoryRealitySnapshot:
        return InventoryRealitySnapshot(sku=sku, system_quantity=system_qty, physical_quantity=physical_qty,
            divergence=physical_qty - system_qty, trust_score=trust_score, last_updated=datetime.now().isoformat())
