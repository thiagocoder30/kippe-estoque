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
