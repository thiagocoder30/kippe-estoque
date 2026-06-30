#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E011.1: CQRS LEDGER REFACTORING (DUAL STOCK VIEW)
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
kippe::banner_program "E" "E011.1" "CQRS Ledger Refactoring"

kippe::step 1 ${TOTAL_STEPS} "Refactoring DualStockView to consume exclusive Ledger Truth..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/movement.py"
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, List, Dict
from src.security.exceptions import BusinessRuleViolation
from src.domain.warehouse.ledger import LedgerEntry

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
    """Intenção/Comando de Movimentação operacional (Write Model)"""
    sku: str
    quantity: int
    movement_type: MovementType
    origin: str
    destination: str
    reason: Optional[str]
    created_at: str

class DualStockView:
    """
    CQRS Read Model para o Estoque Dual.
    Projeta o saldo consumindo estritamente a Fonte da Verdade (LedgerEntry),
    evitando acoplamento com o modelo de escrita.
    """
    @staticmethod
    def calculate(entries: List[LedgerEntry], sku: str) -> Dict[str, int]:
        depot = 0
        store = 0

        for e in entries:
            if e.sku != sku:
                continue

            # Classificação topológica direta:
            # Qualquer localização chamada 'STORE' ou 'LOJA' é Venda.
            # O resto (DEPOT, EST-A, FLOOR-LIMPEZA) é Depósito físico.
            if e.location_id in ("STORE", "LOJA"):
                store += e.quantity
            else:
                depot += e.quantity

        return {
            "depot": depot,
            "store": store,
            "total": depot + store
        }

class MovementEngine:
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

kippe::step 2 ${TOTAL_STEPS} "Updating Movement Registry Tests to match the new CQRS Contract..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/domain/warehouse/test_movement_registry.py"
import pytest
from src.domain.warehouse.movement import MovementEngine, DualStockView
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.security.exceptions import BusinessRuleViolation

def test_movement_engine_registers_fast_event():
    event = MovementEngine.register(
        sku="DETERGENTE-X", quantity=6, movement_type="TO_STORE",
        origin="REPOSITOR_APP", destination="STORE"
    )
    assert event.sku == "DETERGENTE-X"
    assert event.quantity == 6

def test_dual_stock_view_calculates_partitions_from_ledger():
    account = InventoryAccount(sku="DETERGENTE-X")
    
    # 1. Base inicial no depósito (Goods Receipt)
    account.record_transaction("L1", TransactionType.GOODS_RECEIPT, 100, "DEPOT", "NF-1")
    
    # 2. Transferência para a loja (10 un)
    account.record_transaction("L1", TransactionType.TRANSFER_OUT, -10, "DEPOT", "APP")
    account.record_transaction("L1", TransactionType.TRANSFER_IN, 10, "STORE", "APP")
    
    # 3. Transferência para a loja (2 un)
    account.record_transaction("L1", TransactionType.TRANSFER_OUT, -2, "DEPOT", "APP")
    account.record_transaction("L1", TransactionType.TRANSFER_IN, 2, "STORE", "APP")
    
    # 4. Consumo na Loja (Venda PDV: 3 un)
    account.record_transaction("L1", TransactionType.SALE, -3, "STORE", "PDV")
    
    view = DualStockView.calculate(account.entries, sku="DETERGENTE-X")
    
    assert view["depot"] == 88  # 100 - 10 - 2
    assert view["store"] == 9   # 10 + 2 - 3
    assert view["total"] == 97  # 88 + 9

def test_movement_engine_prevents_zero_quantity():
    with pytest.raises(BusinessRuleViolation, match="estritamente positiva"):
        MovementEngine.register("SKU-1", 0, "TO_STORE", "APP", "STORE")
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Platform Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "102" "1.5.0-platform" "E011.1" "SUCCESS"

echo -e "\n[STATUS] Refatoração CQRS Aplicada: DualStockView consome agora a verdadeira fonte de leitura (Ledger)."
exit 0

