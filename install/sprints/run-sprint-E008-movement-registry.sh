#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E008: MOVEMENT MICRO-REGISTRY ENGINE
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
kippe::banner_program "E" "E008" "Movement Micro-Registry Engine"

kippe::step 1 ${TOTAL_STEPS} "Deploying Dual Stock Model & Movement Events (Domain Layer)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/movement.py"
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, List, Dict
from src.security.exceptions import BusinessRuleViolation

MovementType = Literal[
    "TO_STORE",
    "FROM_STORE",
    "CONSUMPTION",
    "ADJUSTMENT",
    "TRANSFER",
    "RETURN_TO_STOCK"
]

@dataclass(frozen=True)
class MovementEvent:
    """
    Evento ultra-leve de registro de movimentação operacional.
    Focado na captura em <5s para garantir adesão.
    """
    sku: str
    quantity: int
    movement_type: MovementType
    origin: str          # ex: "REPOSITOR_APP", "AUDIT"
    destination: str     # ex: "STORE", "DEPOT"
    reason: Optional[str]
    created_at: str

class DualStockView:
    """
    CQRS Read Model para o Estoque Dual (Depósito vs Loja).
    Calcula a realidade particionada a partir dos micro-registros.
    """
    @staticmethod
    def calculate(events: List[MovementEvent], sku: str, base_depot_stock: int = 0) -> Dict[str, int]:
        depot = base_depot_stock
        store = 0

        for e in events:
            if e.sku != sku:
                continue

            if e.movement_type == "TO_STORE":
                depot -= e.quantity
                store += e.quantity
            elif e.movement_type in ("FROM_STORE", "RETURN_TO_STOCK"):
                store -= e.quantity
                depot += e.quantity
            elif e.movement_type == "CONSUMPTION":
                store -= e.quantity
            elif e.movement_type == "ADJUSTMENT":
                depot += e.quantity

        return {
            "depot": depot,
            "store": store,
            "total": depot + store
        }

class MovementEngine:
    """
    Fábrica de registro rápido para evitar a geração de divergências silenciosas.
    """
    @staticmethod
    def register(sku: str, quantity: int, movement_type: MovementType, origin: str, destination: str, reason: Optional[str] = None) -> MovementEvent:
        if quantity <= 0:
            raise BusinessRuleViolation("A quantidade de movimentação deve ser estritamente positiva.")
            
        return MovementEvent(
            sku=sku,
            quantity=quantity,
            movement_type=movement_type,
            origin=origin,
            destination=destination,
            reason=reason,
            created_at=datetime.now().isoformat()
        )
KIPPE_HUNK

# Atualiza a API pública do pacote
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/__init__.py"
from .topology import Warehouse, StorageLocation
from .ledger import InventoryAccount, LedgerEntry, TransactionType
from .balance import BalanceEngine, BalanceProjection
from .smart_sheet import SkuSmartSheet, SmartSheetBuilder
from .replenishment import ReplenishmentEngine, ReplenishmentSuggestion
from .divergence import DivergenceEvent, TrustScore, InventoryRealitySnapshot, DivergenceEngine, TrustScoreEngine, InventoryRealityEngine
from .movement import MovementEvent, MovementType, DualStockView, MovementEngine

__all__ = [
    "Warehouse", "StorageLocation", "InventoryAccount", "LedgerEntry", 
    "TransactionType", "BalanceEngine", "BalanceProjection",
    "SkuSmartSheet", "SmartSheetBuilder",
    "ReplenishmentEngine", "ReplenishmentSuggestion",
    "DivergenceEvent", "TrustScore", "InventoryRealitySnapshot", 
    "DivergenceEngine", "TrustScoreEngine", "InventoryRealityEngine",
    "MovementEvent", "MovementType", "DualStockView", "MovementEngine"
]
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Test Suite for Movement Registry..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/domain/warehouse/test_movement_registry.py"
import pytest
from src.domain.warehouse.movement import MovementEngine, DualStockView
from src.security.exceptions import BusinessRuleViolation

def test_movement_engine_registers_fast_event():
    event = MovementEngine.register(
        sku="DETERGENTE-X",
        quantity=6,
        movement_type="TO_STORE",
        origin="REPOSITOR_APP",
        destination="STORE"
    )
    
    assert event.sku == "DETERGENTE-X"
    assert event.quantity == 6
    assert event.movement_type == "TO_STORE"

def test_dual_stock_view_calculates_partitions():
    # Base inicial: 100 no depósito
    events = [
        MovementEngine.register("DETERGENTE-X", 10, "TO_STORE", "APP", "STORE"),
        MovementEngine.register("DETERGENTE-X", 2, "TO_STORE", "APP", "STORE"),
        MovementEngine.register("DETERGENTE-X", 3, "CONSUMPTION", "PDV", "CLIENT")
    ]
    
    view = DualStockView.calculate(events, sku="DETERGENTE-X", base_depot_stock=100)
    
    # 100 - 10 - 2 = 88 no depósito
    assert view["depot"] == 88
    # 10 + 2 - 3 consumidos = 9 na loja
    assert view["store"] == 9
    # Total = 88 + 9 = 97
    assert view["total"] == 97

def test_movement_engine_prevents_zero_quantity():
    with pytest.raises(BusinessRuleViolation, match="estritamente positiva"):
        MovementEngine.register("SKU-1", 0, "TO_STORE", "APP", "STORE")
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Domain Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "098" "1.5.0-platform" "E008" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.3" \
    "Operational Projections" \
    "E008 (Movement Micro-Registry)" \
    "E009 — Receiving Intelligence" \
    "8/20 Sprints" \
    "ACTIVE"

echo -e "\n[STATUS] Movement Micro-Registry consolidado. O KIPPE agora previne divergências capturando a realidade em tempo real."
exit 0

