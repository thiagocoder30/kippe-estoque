#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E007: DIVERGENCE ENGINE (INVENTORY REALITY)
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

# 1. Carregamento do Framework
source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=3
kippe::banner_program "E" "E007" "Divergence & Trust Engine"

kippe::step 1 ${TOTAL_STEPS} "Deploying Divergence and Trust Models (Domain Layer)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/divergence.py"
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
KIPPE_HUNK

# Exposição da API Pública
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/__init__.py"
from .topology import Warehouse, StorageLocation
from .ledger import InventoryAccount, LedgerEntry, TransactionType
from .balance import BalanceEngine, BalanceProjection
from .smart_sheet import SkuSmartSheet, SmartSheetBuilder
from .replenishment import ReplenishmentEngine, ReplenishmentSuggestion
from .divergence import DivergenceEvent, TrustScore, InventoryRealitySnapshot, DivergenceEngine, TrustScoreEngine, InventoryRealityEngine

__all__ = [
    "Warehouse", "StorageLocation", "InventoryAccount", "LedgerEntry", 
    "TransactionType", "BalanceEngine", "BalanceProjection",
    "SkuSmartSheet", "SmartSheetBuilder",
    "ReplenishmentEngine", "ReplenishmentSuggestion",
    "DivergenceEvent", "TrustScore", "InventoryRealitySnapshot", 
    "DivergenceEngine", "TrustScoreEngine", "InventoryRealityEngine"
]
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Test Suite for Reality & Trust Engines..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/domain/warehouse/test_divergence_engine.py"
from src.domain.warehouse.divergence import DivergenceEngine, TrustScoreEngine, InventoryRealityEngine, DivergenceEvent

def test_divergence_engine_detects_unregistered_withdrawal():
    # Sistema diz 100, Físico diz 92
    event = DivergenceEngine.evaluate(sku="DETERGENTE", system_quantity=100, physical_quantity=92)
    
    assert event is not None
    assert event.delta == -8
    assert event.divergence_type == "UNREGISTERED_WITHDRAWAL"

def test_divergence_engine_detects_expiration_loss():
    event = DivergenceEngine.evaluate(sku="IOGURTE", system_quantity=50, physical_quantity=40, reason="Produto vencido descartado")
    assert event.divergence_type == "EXPIRED_LOSS"

def test_divergence_engine_ignores_perfect_match():
    event = DivergenceEngine.evaluate(sku="CAFE", system_quantity=20, physical_quantity=20)
    assert event is None

def test_trust_score_penalization_math():
    # Simula 4 retiradas não registradas totalizando 20 unidades de erro
    events = [
        DivergenceEvent("SKU-1", 100, 95, -5, "UNREGISTERED_WITHDRAWAL", None, "2026-06-01T10:00:00"),
        DivergenceEvent("SKU-1", 95, 90, -5, "UNREGISTERED_WITHDRAWAL", None, "2026-06-05T10:00:00"),
        DivergenceEvent("SKU-1", 90, 85, -5, "UNREGISTERED_WITHDRAWAL", None, "2026-06-10T10:00:00"),
        DivergenceEvent("SKU-1", 85, 80, -5, "UNREGISTERED_WITHDRAWAL", None, "2026-06-15T10:00:00")
    ]
    
    trust = TrustScoreEngine.calculate(events)
    
    assert trust.divergence_count == 4
    assert trust.total_adjustment_volume == 20
    # Score Base (1.0) - Freq (4*0.05 = 0.20) - Volume (20*0.01 = 0.20) = 0.60
    assert trust.score == 0.60
    assert trust.risk_level == "MEDIUM"

def test_inventory_reality_snapshot_building():
    snapshot = InventoryRealityEngine.build_snapshot(sku="CAFE", system_qty=50, physical_qty=48, trust_score=0.85)
    assert snapshot.divergence == -2
    assert snapshot.trust_score == 0.85
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Domain Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "097" "1.5.0-platform" "E007" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.3" \
    "Operational Projections" \
    "E007 (Divergence & Trust Engine)" \
    "E008 — Movement Micro-Registry" \
    "7/20 Sprints" \
    "ACTIVE"

echo -e "\n[STATUS] Inventory Reality Engine consolidado. KIPPE agora mede a confiabilidade do seu próprio estoque."
exit 0

