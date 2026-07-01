from src.application.warehouse.commands import TransferToStoreCommand
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.domain.catalog.product import ProductCatalogRepository
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.security.exceptions import NotFoundException

class TransferToStoreHandler:
    def __init__(self, ledger_repo: InventoryAccountRepository, catalog_repo: ProductCatalogRepository):
        self.ledger_repo = ledger_repo
        self.catalog_repo = catalog_repo

    def execute(self, cmd: TransferToStoreCommand) -> None:
        if not self.catalog_repo.get_by_sku(cmd.sku):
            raise NotFoundException(f"SKU {cmd.sku} não encontrado no Catálogo de Produtos.")
            
        account = self.ledger_repo.get_by_sku(cmd.sku) or InventoryAccount(sku=cmd.sku)
        
        metadata = {"movement_type": "TO_STORE", "operator": cmd.operator}
        
        account.record_transaction(cmd.batch_code, TransactionType.TRANSFER_OUT, -cmd.quantity, "DEPOT", "APP_MOV", metadata)
        account.record_transaction(cmd.batch_code, TransactionType.TRANSFER_IN, cmd.quantity, "STORE", "APP_MOV", metadata)
        
        self.ledger_repo.save(account)
