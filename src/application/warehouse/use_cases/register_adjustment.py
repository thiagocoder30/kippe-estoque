from src.application.warehouse.commands import RegisterAdjustmentCommand
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.domain.catalog.product import ProductCatalogRepository
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.security.exceptions import NotFoundException

class RegisterAdjustmentHandler:
    def __init__(self, ledger_repo: InventoryAccountRepository, catalog_repo: ProductCatalogRepository):
        self.ledger_repo = ledger_repo
        self.catalog_repo = catalog_repo

    def execute(self, cmd: RegisterAdjustmentCommand) -> None:
        if not self.catalog_repo.get_by_sku(cmd.sku):
            raise NotFoundException(f"SKU {cmd.sku} não encontrado no Catálogo de Produtos.")
            
        account = self.ledger_repo.get_by_sku(cmd.sku) or InventoryAccount(sku=cmd.sku)
        
        metadata = {
            "div_type": cmd.divergence_type,
            "reason": cmd.reason,
            "operator": cmd.operator
        }
        
        account.record_transaction(
            batch_id=cmd.batch_code,
            tx_type=TransactionType.ADJUSTMENT,
            quantity=cmd.quantity,
            location_id="DEPOT",
            reference_document="AUDIT_ADJUSTMENT",
            metadata=metadata
        )
        self.ledger_repo.save(account)
