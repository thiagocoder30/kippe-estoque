#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E006: REPLENISHMENT ENGINE (SMART ASSISTANT)
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
kippe::banner_program "E" "E006" "Replenishment Engine"

kippe::step 1 ${TOTAL_STEPS} "Deploying Replenishment Engine (Domain Service)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/replenishment.py"
from dataclasses import dataclass
from typing import Optional
from src.domain.warehouse.smart_sheet import SkuSmartSheet
from src.security.exceptions import BusinessRuleViolation

@dataclass(frozen=True)
class ReplenishmentSuggestion:
    """
    Representa uma sugestão de compra (Reposição) gerada pelo Assistente.
    """
    sku: str
    current_available: int
    min_stock: int
    ideal_stock: int
    suggested_quantity: int
    urgency: str  # CRITICAL, HIGH, NORMAL

class ReplenishmentEngine:
    """
    Motor do Assistente Inteligente responsável por sugerir compras.
    Baseia-se no saldo disponível calculado pela Smart Sheet.
    """
    @staticmethod
    def calculate(sheet: SkuSmartSheet, min_stock: int, ideal_stock: int) -> Optional[ReplenishmentSuggestion]:
        if min_stock < 0 or ideal_stock < 0:
            raise BusinessRuleViolation("Parâmetros de estoque mínimo e ideal não podem ser negativos.")
            
        if ideal_stock <= min_stock:
            raise BusinessRuleViolation("O estoque ideal deve ser estritamente maior que o estoque mínimo.")

        available = sheet.available_balance
        
        # Se o saldo disponível ainda é seguro (acima do mínimo), não sugere compra
        if available > min_stock:
            return None

        # Calcula o quanto falta para atingir o cenário ideal
        deficit = ideal_stock - available
        
        # Define urgência
        urgency = "NORMAL"
        if available <= 0:
            urgency = "CRITICAL"
        elif available <= (min_stock * 0.5):
            urgency = "HIGH"

        return ReplenishmentSuggestion(
            sku=sheet.sku,
            current_available=available,
            min_stock=min_stock,
            ideal_stock=ideal_stock,
            suggested_quantity=deficit,
            urgency=urgency
        )
KIPPE_HUNK

# Atualiza a API pública do pacote com o novo motor
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/__init__.py"
from .topology import Warehouse, StorageLocation
from .ledger import InventoryAccount, LedgerEntry, TransactionType
from .balance import BalanceEngine, BalanceProjection
from .smart_sheet import SkuSmartSheet, SmartSheetBuilder
from .replenishment import ReplenishmentEngine, ReplenishmentSuggestion

__all__ = [
    "Warehouse", "StorageLocation", "InventoryAccount", "LedgerEntry", 
    "TransactionType", "BalanceEngine", "BalanceProjection",
    "SkuSmartSheet", "SmartSheetBuilder",
    "ReplenishmentEngine", "ReplenishmentSuggestion"
]
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Test Suite for Replenishment Assistant..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/domain/warehouse/test_replenishment.py"
import pytest
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.domain.warehouse.smart_sheet import SmartSheetBuilder
from src.domain.warehouse.replenishment import ReplenishmentEngine
from src.security.exceptions import BusinessRuleViolation

def create_mock_sheet(sku: str, qty: int) -> "SkuSmartSheet":
    account = InventoryAccount(sku=sku)
    if qty > 0:
        account.record_transaction("L1", TransactionType.GOODS_RECEIPT, qty, "A1", "NF-1")
    elif qty < 0:
        # Força saldo negativo para teste de rutura
        account.record_transaction("L1", TransactionType.GOODS_RECEIPT, 1, "A1", "NF-1")
        account.record_transaction("L1", TransactionType.SALE, -abs(qty)-1, "A1", "PED-1")
    return SmartSheetBuilder.build(account)

def test_replenishment_engine_suggests_normal_purchase():
    # Saldo 8, Minimo 10, Ideal 50 -> Sugere comprar 42
    sheet = create_mock_sheet("DETERGENTE", 8)
    suggestion = ReplenishmentEngine.calculate(sheet, min_stock=10, ideal_stock=50)
    
    assert suggestion is not None
    assert suggestion.suggested_quantity == 42
    assert suggestion.urgency == "NORMAL"

def test_replenishment_engine_suggests_high_urgency():
    # Saldo 4, Minimo 10 (saldo <= 50% do mínimo)
    sheet = create_mock_sheet("CAFE", 4)
    suggestion = ReplenishmentEngine.calculate(sheet, min_stock=10, ideal_stock=30)
    
    assert suggestion.urgency == "HIGH"
    assert suggestion.suggested_quantity == 26

def test_replenishment_engine_suggests_critical_urgency_on_stockout():
    # Saldo 0 ou negativo
    sheet = create_mock_sheet("SABAO", 0)
    suggestion = ReplenishmentEngine.calculate(sheet, min_stock=5, ideal_stock=20)
    
    assert suggestion.urgency == "CRITICAL"
    assert suggestion.suggested_quantity == 20

def test_replenishment_engine_ignores_healthy_stock():
    # Saldo 15, Mínimo 10 -> Nenhuma sugestão
    sheet = create_mock_sheet("LEITE", 15)
    suggestion = ReplenishmentEngine.calculate(sheet, min_stock=10, ideal_stock=50)
    
    assert suggestion is None

def test_replenishment_engine_validates_parameters():
    sheet = create_mock_sheet("TESTE", 5)
    
    with pytest.raises(BusinessRuleViolation, match="maior que o estoque mínimo"):
        ReplenishmentEngine.calculate(sheet, min_stock=10, ideal_stock=10)
        
    with pytest.raises(BusinessRuleViolation, match="não podem ser negativos"):
        ReplenishmentEngine.calculate(sheet, min_stock=-5, ideal_stock=20)
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "096" "1.5.0-platform" "E006" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.3" \
    "Operational Projections" \
    "E006 (Replenishment Engine)" \
    "E007 — Divergence Engine" \
    "6/20 Sprints" \
    "ACTIVE"

echo -e "\n[STATUS] Replenishment Engine implantado. Assistente KIPPE agora sugere compras automaticamente."
exit 0

