#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM C: INVENTORY
# SPRINT INV015: REPLENISHMENT ENGINE
# ============================================================
set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"
# 1. Bootstrap (13-Step Frozen Framework)
source install/lib/bootstrap.sh
source install/lib/testing.sh
source install/lib/validation.sh
kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR
TOTAL_STEPS=3
kippe::banner_program "C" "INV015" "Replenishment Engine"
kippe::step 1 ${TOTAL_STEPS} "Applying Domain Mutations: Replenishment Engine Service..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/services/replenishment_engine.py"
from typing import Dict, Any
from src.domain.product import Product
class ReplenishmentEngine:
    # Domain Service: ReplenishmentEngine
    # Motor responsavel por calculos dinamicos de Ponto de Reposicao (PR)
    # e Estoque de Seguranca (ES) baseando-se em dados operacionais.
    @staticmethod
    def calculate_replenishment_metrics(product: Product, average_daily_demand: float, lead_time_days: int, safety_days: int) -> Dict[str, Any]:
        if average_daily_demand < 0 or lead_time_days < 0 or safety_days < 0:
            raise ValueError("As metricas de demanda, lead time e dias de seguranca devem ser positivas.")
        safety_stock = int(average_daily_demand * safety_days)
        reorder_point = int((average_daily_demand * lead_time_days) + safety_stock)
        
        # Consolida a quantidade fisica global disponivel deduzindo as reservas
        available_stock = product.available_quantity
        
        is_replenishment_required = available_stock <= reorder_point
        suggested_order_qty = 0
        
        if is_replenishment_required:
            # Uma heuristica basica corporativa: pedir o suficiente para cobrir PR + ES, 
            # garantindo que o saldo final apos o recebimento estabilize acima da ruptura.
            target_stock = reorder_point + safety_stock
            suggested_order_qty = max(0, target_stock - available_stock)
        return {
            "sku": product.id,
            "available_stock": available_stock,
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
            "is_replenishment_required": is_replenishment_required,
            "suggested_order_quantity": suggested_order_qty
        }
KIPPE_HUNK
# 3. Semantic Validator & 4. AST Compile
kippe::step 2 ${TOTAL_STEPS} "Verifying Code Integrity via Semantic and AST Gates..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
# 5. Regression Suite
kippe::step 3 ${TOTAL_STEPS} "Writing and Executing Replenishment Test Suite..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/test_replenishment_engine.py"
import pytest
from src.domain.product import Product
from src.domain.services.replenishment_engine import ReplenishmentEngine
def test_replenishment_metrics_calculation_triggers_reorder():
    p = Product(id="SKU-REP-1", name="Cimento 50kg", quantity=100) # Saldo de 100
    
    # Demanda: 10/dia | Lead Time: 7 dias | Safety: 5 dias
    # ES = 10 * 5 = 50
    # PR = (10 * 7) + 50 = 120
    # Como 100 <= 120, exige reposicao. Sugestao: 120 + 50 - 100 = 70.
    
    metrics = ReplenishmentEngine.calculate_replenishment_metrics(
        product=p, average_daily_demand=10.0, lead_time_days=7, safety_days=5
    )
    
    assert metrics["safety_stock"] == 50
    assert metrics["reorder_point"] == 120
    assert metrics["is_replenishment_required"] is True
    assert metrics["suggested_order_quantity"] == 70
def test_replenishment_metrics_healthy_stock():
    p = Product(id="SKU-REP-2", name="Tijolo", quantity=300) 
    
    # Demanda: 10/dia | Lead Time: 7 dias | Safety: 5 dias
    # ES = 50, PR = 120. Saldo = 300 (Saudavel)
    
    metrics = ReplenishmentEngine.calculate_replenishment_metrics(
        product=p, average_daily_demand=10.0, lead_time_days=7, safety_days=5
    )
    
    assert metrics["is_replenishment_required"] is False
    assert metrics["suggested_order_quantity"] == 0
def test_replenishment_metrics_validation_error():
    p = Product(id="SKU-REP-3", name="Areia")
    with pytest.raises(ValueError, match="devem ser positivas"):
        ReplenishmentEngine.calculate_replenishment_metrics(p, -5, 7, 5)
KIPPE_HUNK
kippe::test_execute_all
# 6. Architecture Scorecard
cat << "SCORECARD" > "${KIPPE_ROOT}/docs/checkpoints/ARCHITECTURE_SCORECARD-INV015.md"
# Architecture Scorecard - Kippe Platform
### Sprint: INV015 - Replenishment Engine

| Criterio | Status | Detalhes |
| :--- | :--- | :--- |
| **Testes passando** | ✅ | GREEN. Calculos logisticos corporativos atestados. |
| **Formulas de Reposicao** | ✅ | PR (Ponto de Reposicao) e ES (Estoque de Seguranca) validados matematicamente. |
| **Sinal de Ruptura** | ✅ | Gatilho is_replenishment_required disparado com base em saldo liquido. |
| **Gate C.4 (Analytics)** | ✅ | Capacidade analitica expandida para planejamento de ressuprimento. |

SCORECARD
# 7. Checkpoint & 8. Manifest
kippe::checkpoint_create "053" "1.3.0-frozen" "INV015" "SUCCESS"
kippe::manifest_create "INV015" "C" "1.3.0-frozen" "SUCCESS" "INV016"
# Limpeza de resíduos transientes
rm -f data/test_*.db data/test_*.log data/test_*.db-journal 2>/dev/null || true
# 9 a 12. Sincronização Compulsória do Estado Permanente
kippe::governance_sync \
    "C" \
    "Inventory" \
    "2" \
    "Profissional" \
    "C.4" \
    "Analytics" \
    "INV015 (Replenishment Engine)" \
    "INV016 — Negative Stock Policies" \
    "16/20 Sprints" \
    "STABLE"
exit 0
