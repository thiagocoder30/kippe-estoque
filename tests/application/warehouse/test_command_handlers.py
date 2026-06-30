import pytest
from src.application.warehouse.commands import ReceiveGoodsCommand, TransferToStoreCommand, RegisterAdjustmentCommand
from src.application.warehouse.command_handlers import WarehouseCommandHandler
from src.domain.warehouse.ledger import InventoryAccount
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.infrastructure.persistence.memory.product_catalog import InMemoryProductCatalog
from src.security.exceptions import NotFoundException

class InMemoryLedgerRepo(InventoryAccountRepository):
    def __init__(self):
        self.accounts = {}
    def save(self, account: InventoryAccount) -> None:
        self.accounts[account.sku] = account
    def get_by_sku(self, sku: str) -> InventoryAccount:
        return self.accounts.get(sku)

@pytest.fixture
def handler():
    repo = InMemoryLedgerRepo()
    catalog = InMemoryProductCatalog() # Já contém o SKU 789609890001
    return WarehouseCommandHandler(repo, catalog)

def test_handle_receive_goods_creates_account_and_persists_events(handler):
    cmd = ReceiveGoodsCommand(
        sku="789609890001", quantity=100, supplier="YPE", 
        batch_code="B01", expiration_date="2027-01-01", invoice_id="NF-1", operator="Thiago"
    )
    handler.handle_receive_goods(cmd)
    
    account = handler.ledger_repo.get_by_sku("789609890001")
    assert account is not None
    assert len(account.entries) == 1
    assert account.entries[0].quantity == 100
    assert account.entries[0].metadata["supplier"] == "YPE"

def test_handle_transfer_to_store_generates_dual_events(handler):
    handler.handle_receive_goods(ReceiveGoodsCommand("789609890001", 100, "YPE", "B01", None, None, "Admin"))
    
    cmd = TransferToStoreCommand(sku="789609890001", quantity=20, batch_code="B01", operator="Repositor")
    handler.handle_transfer_to_store(cmd)
    
    account = handler.ledger_repo.get_by_sku("789609890001")
    # 1 Recebimento + 1 Saída Depósito + 1 Entrada Loja = 3 eventos
    assert len(account.entries) == 3
    assert account.entries[-1].location_id == "STORE"
    assert account.entries[-1].quantity == 20

def test_handler_rejects_unknown_skus(handler):
    cmd = ReceiveGoodsCommand("SKU_INEXISTENTE", 10, "FORN", "B1", None, None, "Admin")
    with pytest.raises(NotFoundException, match="não encontrado no Catálogo"):
        handler.handle_receive_goods(cmd)
