import os
import json
import tempfile
from typing import Optional, Dict, Any
from src.domain.warehouse.ledger import InventoryAccount, LedgerEntry, TransactionType
from src.domain.warehouse.ledger_repository import InventoryAccountRepository

class JsonLedgerRepository(InventoryAccountRepository):
    """Persistência atómica do Livro-Razão (Event Store) em JSON."""
    def __init__(self, file_path: str = "data/inventory_ledger.json"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def save(self, account: InventoryAccount) -> None:
        data = self._read_all()
        entries = []
        for e in account.entries:
            entries.append({
                "id": e.id, "timestamp": e.timestamp, "sku": e.sku,
                "batch_id": e.batch_id, "transaction_type": e.transaction_type.name,
                "quantity": e.quantity, "location_id": e.location_id,
                "reference_document": e.reference_document, "metadata": e.metadata
            })
        data[account.sku] = {"sku": account.sku, "entries": entries}
        self._atomic_write(data)

    def get_by_sku(self, sku: str) -> Optional[InventoryAccount]:
        data = self._read_all()
        if sku not in data:
            return None
        raw = data[sku]
        account = InventoryAccount(sku=sku)
        for e in raw["entries"]:
            entry = LedgerEntry(
                id=e["id"], timestamp=e["timestamp"], sku=e["sku"],
                batch_id=e["batch_id"], transaction_type=TransactionType[e["transaction_type"]],
                quantity=e["quantity"], location_id=e["location_id"],
                reference_document=e["reference_document"], metadata=e["metadata"]
            )
            account.entries.append(entry)
        return account

    def _read_all(self) -> Dict[str, Any]:
        if not os.path.exists(self.file_path): return {}
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _atomic_write(self, data: Dict[str, Any]) -> None:
        dir_name = os.path.dirname(self.file_path)
        fd, tmp = tempfile.mkstemp(dir=dir_name, suffix=".json")
        with os.fdopen(fd, 'w', encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.file_path)
