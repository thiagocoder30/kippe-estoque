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
