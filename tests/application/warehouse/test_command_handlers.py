import pytest
from src.application.warehouse.commands import ReceiveGoodsCommand, TransferToStoreCommand, RegisterAdjustmentCommand
from src.application.warehouse.command_bus import CommandBus
from src.application.warehouse.use_cases.receive_goods import ReceiveGoodsHandler
from src.application.warehouse.use_cases.transfer_to_store import TransferToStoreHandler
from src.application.warehouse.use_cases.register_adjustment import RegisterAdjustmentHandler
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
    def get_all(self):
        return list(self.accounts.values())

@pytest.fixture
def bus_and_repo():
    repo = InMemoryLedgerRepo()
    catalog = InMemoryProductCatalog() # Contém SKU 789609890001
    
    bus = CommandBus()
    bus.register(ReceiveGoodsCommand, ReceiveGoodsHandler(repo, catalog))
    bus.register(TransferToStoreCommand, TransferToStoreHandler(repo, catalog))
    bus.register(RegisterAdjustmentCommand, RegisterAdjustmentHandler(repo, catalog))
    
    return bus, repo

def test_receive_goods_dispatched_correctly(bus_and_repo):
    bus, repo = bus_and_repo
    cmd = ReceiveGoodsCommand(
        sku="789609890001", quantity=100, supplier="YPE", 
        batch_code="B01", expiration_date="2027-01-01", invoice_id="NF-1", operator="Thiago"
    )
    
    bus.dispatch(cmd)
    
    account = repo.get_by_sku("789609890001")
    assert account is not None
    assert len(account.entries) == 1
    assert account.entries[0].quantity == 100

def test_transfer_to_store_dispatched_correctly(bus_and_repo):
    bus, repo = bus_and_repo
    bus.dispatch(ReceiveGoodsCommand("789609890001", 100, "YPE", "B01", None, None, "Admin"))
    
    bus.dispatch(TransferToStoreCommand("789609890001", 20, "B01", "Repositor"))
    
    account = repo.get_by_sku("789609890001")
    assert len(account.entries) == 3
    assert account.entries[-1].location_id == "STORE"

def test_unregistered_command_raises_error():
    bus = CommandBus()
    class DummyCommand: pass
    
    with pytest.raises(ValueError, match="Nenhum handler registado para o comando"):
        bus.dispatch(DummyCommand())
