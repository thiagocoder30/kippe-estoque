import pytest
from src.application.warehouse.projections.engine import ProjectionEngine
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

def test_projection_engine_builds_all_projections():
    repo = InMemoryLedgerRepo()
    catalog = InMemoryProductCatalog() # Contém 789609890001
    
    # Mock de histórico
    acc = InventoryAccount(sku="789609890001")
    acc.record_transaction("L1", TransactionType.GOODS_RECEIPT, 10, "DEPOT", "NF", {"expiration_date": "2027-01-01"})
    repo.save(acc)
    
    engine = ProjectionEngine(repo, catalog)
    inv, exp, pur = engine.build_all()
    
    assert inv.total_skus == 1
    assert inv.total_items == 10
    # O produto recebeu reposição, não tem divergência, trust é 100
    assert inv.avg_trust_score == 100.0
    
    # Validação estrutural de que as projeções saem formatadas prontas para a UI
    assert hasattr(exp, 'expiring_in_7_days')
    assert hasattr(pur, 'urgent_replenishment')
