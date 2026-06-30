#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E004: INVENTORY BALANCE ENGINE (CQRS READ MODEL)
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
kippe::banner_program "E" "E004" "Inventory Balance Engine"

kippe::step 1 ${TOTAL_STEPS} "Deploying Balance Projection Engine (Domain Service)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/balance.py"
from dataclasses import dataclass, field
from typing import Dict
from src.domain.warehouse.ledger import InventoryAccount

@dataclass(frozen=True)
class BalanceProjection:
    """
    Read Model (CQRS).
    Representa a projeção do saldo em um dado momento.
    """
    total: int
    by_batch: Dict[str, int] = field(default_factory=dict)
    by_location: Dict[str, int] = field(default_factory=dict)

class BalanceEngine:
    """
    Domain Service responsável por calcular (projetar) o saldo
    a partir de um histórico imutável de transações (Event Sourcing).
    Nenhum saldo é armazenado estaticamente; tudo é matemática pura.
    """
    @staticmethod
    def calculate(account: InventoryAccount) -> BalanceProjection:
        total = 0
        by_batch: Dict[str, int] = {}
        by_location: Dict[str, int] = {}

        for entry in account.entries:
            total += entry.quantity
            
            # Projeção por Lote (Crucial para o futuro Allocation/FEFO)
            by_batch[entry.batch_id] = by_batch.get(entry.batch_id, 0) + entry.quantity
            
            # Projeção por Localização Física (Lean Topology: A1, FLOOR-LIMPEZA, etc.)
            by_location[entry.location_id] = by_location.get(entry.location_id, 0) + entry.quantity

        # Filtra locais/lotes que zeraram para limpar a projeção
        by_batch = {k: v for k, v in by_batch.items() if v != 0}
        by_location = {k: v for k, v in by_location.items() if v != 0}

        return BalanceProjection(
            total=total,
            by_batch=by_batch,
            by_location=by_location
        )
KIPPE_HUNK

# Atualiza a API pública do pacote
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/__init__.py"
from .topology import Warehouse, StorageLocation
from .ledger import InventoryAccount, LedgerEntry, TransactionType
from .balance import BalanceEngine, BalanceProjection

__all__ = [
    "Warehouse",
    "StorageLocation",
    "InventoryAccount",
    "LedgerEntry",
    "TransactionType",
    "BalanceEngine",
    "BalanceProjection"
]
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Test Suite for Balance Engine..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/domain/warehouse/test_balance_engine.py"
import pytest
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.domain.warehouse.balance import BalanceEngine

def test_balance_engine_calculates_total_inventory():
    account = InventoryAccount(sku="DETERGENTE-X")
    
    # +120 Entrada no Chão
    account.record_transaction("L2408", TransactionType.GOODS_RECEIPT, 120, "FLOOR-LIMPEZA", "NF-1")
    # -20 Venda do Chão
    account.record_transaction("L2408", TransactionType.SALE, -20, "FLOOR-LIMPEZA", "PED-1")
    # -10 Transferência do Chão para Estante
    account.record_transaction("L2408", TransactionType.TRANSFER_OUT, -10, "FLOOR-LIMPEZA", "MOV-1")
    # +10 Transferência chegando na Estante
    account.record_transaction("L2408", TransactionType.TRANSFER_IN, 10, "EST-A-01", "MOV-1")
    
    projection = BalanceEngine.calculate(account)
    
    # 120 - 20 - 10 + 10 = 100
    assert projection.total == 100
    
    # O Lote manteve-se o mesmo em todas as operações
    assert len(projection.by_batch) == 1
    assert projection.by_batch["L2408"] == 100
    
    # Projeção Espacial Lean
    assert len(projection.by_location) == 2
    assert projection.by_location["FLOOR-LIMPEZA"] == 90
    assert projection.by_location["EST-A-01"] == 10

def test_balance_engine_cleans_up_zero_balances():
    account = InventoryAccount(sku="CAFE-PILAO-500G")
    
    # Compra 50 unidades para A1
    account.record_transaction("LOTE-X", TransactionType.GOODS_RECEIPT, 50, "EST-C-01", "NF-2")
    # Vende todas as 50
    account.record_transaction("LOTE-X", TransactionType.SALE, -50, "EST-C-01", "PED-2")
    
    projection = BalanceEngine.calculate(account)
    
    assert projection.total == 0
    # Como zerou, os lotes e locais não devem figurar na projeção ativa
    assert "LOTE-X" not in projection.by_batch
    assert "EST-C-01" not in projection.by_location
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Domain Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "094" "1.5.0-platform" "E004" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.2" \
    "Inventory Ledger" \
    "E004 (Balance Engine CQRS)" \
    "E005 — Allocation Engine" \
    "4/20 Sprints" \
    "ACTIVE"

echo -e "\n[STATUS] Balance Engine CQRS (E004) consolidado. Projeções matemáticas em tempo real ativadas."
exit 0

