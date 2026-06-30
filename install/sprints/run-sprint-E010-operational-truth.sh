#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E010: OPERATIONAL TRUTH DASHBOARD (DECISION LAYER)
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
kippe::banner_program "E" "E010" "Operational Truth Engine"

kippe::step 1 ${TOTAL_STEPS} "Deploying Decision Compression Layer (Domain Models)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/operational_truth.py"
from dataclasses import dataclass
from typing import Literal, Dict

ActionPriority = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]

@dataclass(frozen=True)
class OperationalInsight:
    """O único artefato que o operador humano precisa ler."""
    sku: str
    title: str
    message: str
    priority: ActionPriority
    suggested_action: str

class OperationalTruthEngine:
    """
    Motor de Compressão de Decisão.
    Consome matemática complexa (E006-E009) e emite diretrizes táticas simplificadas.
    """
    @staticmethod
    def evaluate(
        sku: str,
        stock_total: int,
        divergence_penalty: float, # 0.0 (sem penalidade) a 1.0 (alta penalidade)
        trust_score: float,        # 0.0 (não confiável) a 1.0 (confiável)
        inbound_risk: float        # 0.0 (baixo risco) a 1.0 (alto risco na origem)
    ) -> OperationalInsight:
        
        # O cálculo funde a confiabilidade da história (trust), 
        # do presente (divergência) e do passado (origem)
        risk = (
            ((1.0 - trust_score) * 0.4) +
            (divergence_penalty * 0.4) +
            (inbound_risk * 0.2)
        )

        # Matriz de Decisão Operacional
        if risk > 0.8:
            priority = "CRITICAL"
            action = "PARALISAR COMPRAS. AUDITORIA IMEDIATA EXIGIDA."
        elif risk > 0.5:
            priority = "HIGH"
            action = "VERIFICAR FÍSICO ANTES DE QUALQUER NOVA MOVIMENTAÇÃO."
        elif risk > 0.3:
            priority = "MEDIUM"
            action = "MONITORIZAR SKU. PRECISÃO EM QUEDA."
        else:
            priority = "LOW"
            action = "OPERAÇÃO NORMAL."

        # Intervenção de Reposição Saudável (apenas se o risco for suportável)
        if stock_total < 10 and risk < 0.5:
            action = "CRIAR ORDEM DE REPOSIÇÃO (BAIXO RISCO OPERACIONAL)."
        elif stock_total < 10 and risk >= 0.5:
            action = "ESTOQUE BAIXO, MAS RISCO ALTO. AUDITAR ANTES DE COMPRAR."

        return OperationalInsight(
            sku=sku,
            title=f"STATUS {sku}: {priority}",
            message=f"Nível de Risco Operacional: {round(risk, 2)}",
            priority=priority,
            suggested_action=action
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
from .movement import MovementEvent, MovementType, DualStockView, MovementEngine
from .receiving import ReceivingEvent, EvaluatedBatch, BatchIntelligenceEngine, ReceivingEngine
from .operational_truth import ActionPriority, OperationalInsight, OperationalTruthEngine

__all__ = [
    "Warehouse", "StorageLocation", "InventoryAccount", "LedgerEntry", 
    "TransactionType", "BalanceEngine", "BalanceProjection",
    "SkuSmartSheet", "SmartSheetBuilder",
    "ReplenishmentEngine", "ReplenishmentSuggestion",
    "DivergenceEvent", "TrustScore", "InventoryRealitySnapshot", 
    "DivergenceEngine", "TrustScoreEngine", "InventoryRealityEngine",
    "MovementEvent", "MovementType", "DualStockView", "MovementEngine",
    "ReceivingEvent", "EvaluatedBatch", "BatchIntelligenceEngine", "ReceivingEngine",
    "ActionPriority", "OperationalInsight", "OperationalTruthEngine"
]
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Test Suite for Operational Truth Engine..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/domain/warehouse/test_operational_truth.py"
from src.domain.warehouse.operational_truth import OperationalTruthEngine

def test_operational_truth_evaluates_healthy_sku():
    insight = OperationalTruthEngine.evaluate(
        sku="CAFE-PILAO",
        stock_total=50,
        divergence_penalty=0.0,
        trust_score=1.0, # 100% confiável
        inbound_risk=0.0
    )
    
    assert insight.priority == "LOW"
    assert "OPERAÇÃO NORMAL" in insight.suggested_action

def test_operational_truth_evaluates_critical_risk():
    insight = OperationalTruthEngine.evaluate(
        sku="SABAO-PO",
        stock_total=100,
        divergence_penalty=0.9, # Alta divergência recente
        trust_score=0.2,        # Histórico terrível
        inbound_risk=0.8        # Lote cego (sem NF/Validade)
    )
    
    assert insight.priority == "CRITICAL"
    assert "PARALISAR COMPRAS" in insight.suggested_action

def test_operational_truth_blocks_blind_replenishment():
    # Estoque baixo (5), mas com risco elevado
    insight = OperationalTruthEngine.evaluate(
        sku="DETERGENTE",
        stock_total=5,
        divergence_penalty=0.6,
        trust_score=0.4,
        inbound_risk=0.5
    )
    
    assert insight.priority == "HIGH"
    assert "AUDITAR ANTES DE COMPRAR" in insight.suggested_action

def test_operational_truth_suggests_safe_replenishment():
    # Estoque baixo (5) num ambiente seguro
    insight = OperationalTruthEngine.evaluate(
        sku="LEITE",
        stock_total=5,
        divergence_penalty=0.0,
        trust_score=0.9,
        inbound_risk=0.1
    )
    
    assert insight.priority == "LOW"
    assert "CRIAR ORDEM DE REPOSIÇÃO" in insight.suggested_action
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Domain Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "100" "1.5.0-platform" "E010" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.5" \
    "Operational Truth" \
    "E010 (Operational Truth Engine)" \
    "PROGRAM E DOMAIN CONCLUDED" \
    "10/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Operational Truth Engine consolidado. O KIPPE traduz agora a complexidade do armazém em ações humanas diretas."
exit 0

