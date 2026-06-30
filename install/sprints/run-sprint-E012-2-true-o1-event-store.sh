#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E012.2: TRUE O(1) EVENT STORE & UNCOMMITTED EVENTS
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
kippe::banner_program "E" "E012.2" "True O(1) Event Store (Uncommitted Events)"

kippe::step 1 ${TOTAL_STEPS} "Applying Uncommitted Events Pattern to Aggregate Root (Domain)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/ledger.py"
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any
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
    id: str
    timestamp: str
    sku: str
    batch_id: str
    transaction_type: TransactionType
    quantity: int
    location_id: str
    reference_document: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class InventoryAccount:
    """
    Aggregate Root do Inventário.
    Mantém o histórico completo (entries) para cálculos de domínio e 
    eventos pendentes (_uncommitted_events) para persistência O(1).
    """
    sku: str
    entries: List[LedgerEntry] = field(default_factory=list)
    _uncommitted_events: List[LedgerEntry] = field(default_factory=list, repr=False)

    def record_transaction(self, batch_id: str, tx_type: TransactionType, quantity: int, location_id: str, reference_document: str, metadata: dict = None) -> LedgerEntry:
        if quantity == 0:
            raise BusinessRuleViolation("A quantidade de uma transação no Ledger não pode ser zero.")
            
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
            reference_document=reference_document,
            metadata=metadata or {}
        )
        self.entries.append(entry)
        self._uncommitted_events.append(entry) # Regista a intenção de gravação
        return entry

    def get_uncommitted_events(self) -> List[LedgerEntry]:
        return self._uncommitted_events.copy()

    def clear_uncommitted_events(self) -> None:
        self._uncommitted_events.clear()
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Refactoring JSONL Repository for True O(1) Append..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/persistence/json/ledger_repository.py"
import os
import json
from typing import Optional
from src.domain.warehouse.ledger import InventoryAccount, LedgerEntry, TransactionType
from src.domain.warehouse.ledger_repository import InventoryAccountRepository

class JsonLinesLedgerRepository(InventoryAccountRepository):
    """
    Persistência O(1) estrita.
    Consome apenas os eventos não submetidos do Agregado, sem ler o histórico.
    """
    def __init__(self, file_path: str = "data/ledger/events.jsonl"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def save(self, account: InventoryAccount) -> None:
        uncommitted = account.get_uncommitted_events()
        if not uncommitted:
            return

        # Escrita puramente O(1)
        with open(self.file_path, "a", encoding="utf-8") as f:
            for e in uncommitted:
                record = {
                    "id": e.id, "timestamp": e.timestamp, "sku": e.sku,
                    "batch_id": e.batch_id, "transaction_type": e.transaction_type.name,
                    "quantity": e.quantity, "location_id": e.location_id,
                    "reference_document": e.reference_document, "metadata": e.metadata
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                
        # Limpa o estado após sucesso
        account.clear_uncommitted_events()

    def get_by_sku(self, sku: str) -> Optional[InventoryAccount]:
        if not os.path.exists(self.file_path):
            return None
        
        account = InventoryAccount(sku=sku)
        has_data = False
        
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                e = json.loads(line)
                if e["sku"] == sku:
                    has_data = True
                    entry = LedgerEntry(
                        id=e["id"], timestamp=e["timestamp"], sku=e["sku"],
                        batch_id=e["batch_id"], transaction_type=TransactionType[e["transaction_type"]],
                        quantity=e["quantity"], location_id=e["location_id"],
                        reference_document=e["reference_document"], metadata=e["metadata"]
                    )
                    # Bypass da regra de negócio para carregamento (hidratar sem gerar uncommitted)
                    account.entries.append(entry)
                    
        return account if has_data else None
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Platform Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "107" "1.5.0-platform" "E012.2" "SUCCESS"

echo -e "\n[STATUS] Uncommitted Events integrados. A escrita no Ledger agora é estritamente O(1)!"
exit 0

