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
