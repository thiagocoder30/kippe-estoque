from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, List

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
    score: float  # 0.0 (não confiável) a 1.0 (totalmente confiável)
    divergence_count: int
    total_adjustment_volume: int
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL

@dataclass(frozen=True)
class InventoryRealitySnapshot:
    sku: str
    system_quantity: int
    physical_quantity: int
    divergence: int
    trust_score: float
    last_updated: str

class DivergenceEngine:
    """Motor que compara o sistema com o mundo físico e gera eventos de divergência."""
    @staticmethod
    def evaluate(sku: str, system_quantity: int, physical_quantity: int, reason: Optional[str] = None) -> Optional[DivergenceEvent]:
        delta = physical_quantity - system_quantity

        if delta == 0:
            return None

        divergence_type = DivergenceEngine._classify(delta, reason)

        return DivergenceEvent(
            sku=sku,
            system_quantity=system_quantity,
            physical_quantity=physical_quantity,
            delta=delta,
            divergence_type=divergence_type,
            reason=reason,
            created_at=datetime.now().isoformat()
        )

    @staticmethod
    def _classify(delta: int, reason: Optional[str]) -> DivergenceType:
        if reason and "venc" in reason.lower():
            return "EXPIRED_LOSS"
        if delta < 0:
            return "UNREGISTERED_WITHDRAWAL"
        if delta > 0:
            return "PHYSICAL_COUNT_CORRECTION"
        return "SYSTEM_ERROR"

class TrustScoreEngine:
    """Calcula a confiabilidade de um SKU baseado no histórico de divergências."""
    @staticmethod
    def calculate(events: List[DivergenceEvent]) -> TrustScore:
        if not events:
            return TrustScore(
                sku="UNKNOWN", score=1.0, divergence_count=0,
                total_adjustment_volume=0, risk_level="LOW"
            )

        total_delta = sum(abs(e.delta) for e in events)
        count = len(events)
        score = 1.0

        # Penaliza frequência (5% por evento)
        score -= min(0.5, count * 0.05)
        # Penaliza volume de erro (1% por unidade perdida/sobrando)
        score -= min(0.5, total_delta * 0.01)

        score = max(0.0, score)

        if score >= 0.8: risk = "LOW"
        elif score >= 0.5: risk = "MEDIUM"
        elif score >= 0.2: risk = "HIGH"
        else: risk = "CRITICAL"

        return TrustScore(
            sku=events[0].sku, score=round(score, 2), divergence_count=count,
            total_adjustment_volume=total_delta, risk_level=risk
        )

class InventoryRealityEngine:
    """Constrói o snapshot final que alimentará reposições e dashboards."""
    @staticmethod
    def build_snapshot(sku: str, system_qty: int, physical_qty: int, trust_score: float) -> InventoryRealitySnapshot:
        return InventoryRealitySnapshot(
            sku=sku,
            system_quantity=system_qty,
            physical_quantity=physical_qty,
            divergence=physical_qty - system_qty,
            trust_score=trust_score,
            last_updated=datetime.now().isoformat()
        )
