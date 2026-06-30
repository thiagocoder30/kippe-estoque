import pytest
import os
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.infrastructure.persistence.json.ledger_repository import JsonLinesLedgerRepository

def test_jsonl_ledger_append_only_persistence(tmp_path):
    file_path = tmp_path / "events.jsonl"
    repo = JsonLinesLedgerRepository(file_path=str(file_path))
    
    account = InventoryAccount(sku="SKU-123")
    account.record_transaction("L1", TransactionType.GOODS_RECEIPT, 10, "A1", "NF-1")
    repo.save(account)
    
    # Valida escrita O(1) (Adicionando novo evento)
    account.record_transaction("L1", TransactionType.SALE, -2, "STORE", "PDV-1")
    repo.save(account)
    
    loaded = repo.get_by_sku("SKU-123")
    assert loaded is not None
    assert len(loaded.entries) == 2
    
    # Verifica o ficheiro físico
    with open(file_path, "r") as f:
        lines = f.readlines()
        assert len(lines) == 2
