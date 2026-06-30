import os
import json
from typing import Optional
from src.domain.warehouse.ledger import InventoryAccount, LedgerEntry, TransactionType
from src.domain.warehouse.ledger_repository import InventoryAccountRepository

class JsonLinesLedgerRepository(InventoryAccountRepository):
    """
    Persistência O(1) baseada em ficheiros JSONL (JSON Lines).
    Opera como um verdadeiro Event Store Append-Only, imune a corrupções de reescrita.
    """
    def __init__(self, file_path: str = "data/ledger/events.jsonl"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def save(self, account: InventoryAccount) -> None:
        # Recupera IDs já gravados para este SKU para não duplicar eventos 
        # (Em produção, o agregado guardaria 'uncommitted_events' em vez de iterarmos tudo)
        existing_ids = set()
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    data = json.loads(line)
                    if data["sku"] == account.sku:
                        existing_ids.add(data["id"])

        # Append-only (O(1) escrita)
        with open(self.file_path, "a", encoding="utf-8") as f:
            for e in account.entries:
                if e.id not in existing_ids:
                    record = {
                        "id": e.id, "timestamp": e.timestamp, "sku": e.sku,
                        "batch_id": e.batch_id, "transaction_type": e.transaction_type.name,
                        "quantity": e.quantity, "location_id": e.location_id,
                        "reference_document": e.reference_document, "metadata": e.metadata
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

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
                    account.entries.append(entry)
                    
        return account if has_data else None
