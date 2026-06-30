from src.infrastructure.persistence.json.ledger_repository import JsonLinesLedgerRepository
from src.domain.warehouse.ledger import InventoryAccount, TransactionType

def generate_seed():
    repo = JsonLinesLedgerRepository()
    account = InventoryAccount(sku="789609890001")
    
    account.record_transaction("L240621", TransactionType.GOODS_RECEIPT, 148, "DEPOT", "NF-123",
        {"supplier": "YPE", "expiration_date": "2026-11-15", "conferente": "Thiago"})
    
    account.record_transaction("L240621", TransactionType.TRANSFER_OUT, -16, "DEPOT", "APP",
        {"movement_type": "TO_STORE"})
    account.record_transaction("L240621", TransactionType.TRANSFER_IN, 16, "STORE", "APP",
        {"movement_type": "TO_STORE"})
    
    account.record_transaction("L240621", TransactionType.ADJUSTMENT, -3, "DEPOT", "AUDIT",
        {"div_type": "UNREGISTERED_WITHDRAWAL", "reason": "Retirada não registada - Analisado pelo Thiago"})
    
    repo.save(account)
    print("✓ Base de Dados do Ledger (Event Store O(1)) populada com sucesso!")

if __name__ == "__main__":
    generate_seed()
