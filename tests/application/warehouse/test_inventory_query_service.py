import pytest
from src.application.warehouse.query_service import InventoryQueryService
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.infrastructure.persistence.memory.product_catalog import InMemoryProductCatalog

class InMemoryLedgerRepo(InventoryAccountRepository):
    def __init__(self):
        self.accounts = {}
    def save(self, account: InventoryAccount) -> None:
        self.accounts[account.sku] = account
    def get_by_sku(self, sku: str) -> InventoryAccount:
        return self.accounts.get(sku)
    def get_all(self):
        return list(self.accounts.values())

def build_scenario(repo):
    account = InventoryAccount(sku="789609890001")
    account.record_transaction("L240621", TransactionType.GOODS_RECEIPT, 148, "DEPOT", "NF-123", 
        {"supplier": "YPE", "expiration_date": "2026-11-15"})
    account.record_transaction("L240621", TransactionType.ADJUSTMENT, -3, "DEPOT", "AUDIT", 
        {"div_type": "UNREGISTERED_WITHDRAWAL", "reason": "Retirada não registrada"})
    repo.save(account)

def test_inventory_query_service_produces_unified_view():
    repo = InMemoryLedgerRepo()
    catalog = InMemoryProductCatalog() # Injeta a dependência necessária
    build_scenario(repo)
    
    service = InventoryQueryService(repo, catalog)
    view = service.get_sku_view("789609890001", min_stock=40, ideal_stock=120)
    
    assert view.sku == "789609890001"
    assert view.description == "Detergente Ypê 500 ml" # Vem do Catálogo
    assert view.available_total == 145
