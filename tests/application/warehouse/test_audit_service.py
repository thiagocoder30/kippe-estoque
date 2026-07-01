import pytest
from src.application.warehouse.audit_service import InventoryAuditService
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

def test_inventory_audit_service_detects_critical_skus():
    repo = InMemoryLedgerRepo()
    catalog = InMemoryProductCatalog()
    
    # Simula um SKU altamente problemático
    account = InventoryAccount(sku="789609890001")
    account.record_transaction("L1", TransactionType.GOODS_RECEIPT, 100, "DEPOT", "NF")
    account.record_transaction("L1", TransactionType.ADJUSTMENT, -5, "DEPOT", "AUDIT", {"div_type": "UNREGISTERED_WITHDRAWAL"})
    account.record_transaction("L1", TransactionType.ADJUSTMENT, -2, "DEPOT", "AUDIT", {"div_type": "UNREGISTERED_WITHDRAWAL"})
    repo.save(account)
    
    audit_svc = InventoryAuditService(repo, catalog)
    report = audit_svc.run_global_audit(["789609890001"])
    
    assert report.total_skus_audited == 1
    assert report.total_system_events == 3
    assert len(report.critical_skus) == 1
    
    crit_sku = report.critical_skus[0]
    assert crit_sku.unregistered_withdrawals == 2
    assert crit_sku.total_adjustments == 2
    # 2 ajustes em 3 eventos = ~66% de taxa de erro
    assert crit_sku.compliance_status == "CRITICAL"
