#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E003: INVENTORY LEDGER (APPEND-ONLY EVENT SOURCING)
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=3
kippe::banner_program "E" "E003" "Inventory Ledger"

# Preparação de Diretórios
touch "${KIPPE_ROOT}/src/domain/warehouse/__init__.py"

kippe::step 1 ${TOTAL_STEPS} "Deploying Immutable Inventory Ledger (Domain Layer)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/ledger.py"
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List
from src.security.exceptions import BusinessRuleViolation

class TransactionType(Enum):
    GOODS_RECEIPT = "GOODS_RECEIPT"
    SALE = "SALE"
    TRANSFER_OUT = "TRANSFER_OUT"
    TRANSFER_IN = "TRANSFER_IN"
    ADJUSTMENT = "ADJUSTMENT"
    CYCLE_COUNT = "CYCLE_COUNT"

@dataclass(frozen=True)
class LedgerEntry:
    """
    Value Object Imutável.
    Representa um evento único na linha do tempo do estoque.
    O saldo não mora aqui; aqui moram os fatos matemáticos.
    """
    id: str
    timestamp: str
    sku: str
    batch_id: str
    transaction_type: TransactionType
    quantity: int  # Positivo (+) para entradas, Negativo (-) para saídas
    location_id: str
    reference_document: str

@dataclass
class InventoryAccount:
    """
    Aggregate Root do Inventário.
    Atua como uma "Conta Bancária" para um SKU específico.
    """
    sku: str
    entries: List[LedgerEntry] = field(default_factory=list)

    def record_transaction(self, batch_id: str, tx_type: TransactionType, quantity: int, location_id: str, reference_document: str) -> LedgerEntry:
        if quantity == 0:
            raise BusinessRuleViolation("A quantidade de uma transação no Ledger não pode ser zero.")
            
        # Garante a direção matemática do fluxo baseado no tipo de transação
        if tx_type in [TransactionType.SALE, TransactionType.TRANSFER_OUT] and quantity > 0:
            raise BusinessRuleViolation(f"Transações do tipo {tx_type.value} exigem quantidades negativas.")
            
        if tx_type in [TransactionType.GOODS_RECEIPT, TransactionType.TRANSFER_IN] and quantity < 0:
            raise BusinessRuleViolation(f"Transações do tipo {tx_type.value} exigem quantidades positivas.")

        entry = LedgerEntry(
            id=uuid.uuid4().hex[:12].upper(),
            timestamp=datetime.now().isoformat(),
            sku=self.sku,
            batch_id=batch_id,
            transaction_type=tx_type,
            quantity=quantity,
            location_id=location_id,
            reference_document=reference_document
        )
        self.entries.append(entry)
        return entry
KIPPE_HUNK

# Expondo o novo agregado na API pública do pacote
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/__init__.py"
from .topology import Warehouse, StorageLocation
from .ledger import InventoryAccount, LedgerEntry, TransactionType

__all__ = [
    "Warehouse",
    "StorageLocation",
    "InventoryAccount",
    "LedgerEntry",
    "TransactionType"
]
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Ledger Repository Interface..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/ledger_repository.py"
from abc import ABC, abstractmethod
from typing import Optional
from src.domain.warehouse.ledger import InventoryAccount

class InventoryAccountRepository(ABC):
    """Porta de saída para a persistência do Livro-Razão (Event Store)."""
    @abstractmethod
    def save(self, account: InventoryAccount) -> None:
        pass

    @abstractmethod
    def get_by_sku(self, sku: str) -> Optional[InventoryAccount]:
        pass
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Deploying Domain Unit Tests for Ledger Invariants..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/domain/warehouse/test_inventory_ledger.py"
import pytest
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.security.exceptions import BusinessRuleViolation

def test_inventory_account_records_receipt_correctly():
    account = InventoryAccount(sku="SKU-789")
    
    entry = account.record_transaction(
        batch_id="L240601",
        tx_type=TransactionType.GOODS_RECEIPT,
        quantity=24,
        location_id="C2",
        reference_document="PO-00034"
    )
    
    assert len(account.entries) == 1
    assert entry.quantity == 24
    assert entry.transaction_type == TransactionType.GOODS_RECEIPT
    assert entry.location_id == "C2"

def test_inventory_account_enforces_negative_quantity_for_sales():
    account = InventoryAccount(sku="SKU-789")
    
    with pytest.raises(BusinessRuleViolation, match="exigem quantidades negativas"):
        account.record_transaction(
            batch_id="L240601",
            tx_type=TransactionType.SALE,
            quantity=5, # Erro: Venda deve ser negativa (-5)
            location_id="C2",
            reference_document="INV-999"
        )
        
    # Validando o caso correto
    entry = account.record_transaction("L240601", TransactionType.SALE, -5, "C2", "INV-999")
    assert entry.quantity == -5

def test_inventory_account_prevents_zero_quantity():
    account = InventoryAccount(sku="SKU-789")
    with pytest.raises(BusinessRuleViolation, match="não pode ser zero"):
        account.record_transaction("L1", TransactionType.ADJUSTMENT, 0, "A1", "ADJ-1")
KIPPE_HUNK

kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "093" "1.5.0-platform" "E003" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.2" \
    "Inventory Ledger" \
    "E003 (Ledger Domain)" \
    "E004 — Balance Engine" \
    "3/20 Sprints" \
    "ACTIVE"

echo -e "\n[STATUS] Inventory Ledger (Event Sourcing) inaugurado com sucesso."
exit 0

