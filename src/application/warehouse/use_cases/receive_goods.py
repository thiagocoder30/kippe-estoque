from src.application.warehouse.commands import ReceiveGoodsCommand
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.domain.catalog.product import ProductCatalogRepository
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.security.exceptions import NotFoundException

class ReceiveGoodsHandler:
    def __init__(self, ledger_repo: InventoryAccountRepository, catalog_repo: ProductCatalogRepository):
        self.ledger_repo = ledger_repo
        self.catalog_repo = catalog_repo

    def execute(self, cmd: ReceiveGoodsCommand) -> None:
        if not self.catalog_repo.get_by_sku(cmd.sku):
            raise NotFoundException(f"SKU {cmd.sku} não encontrado no Catálogo de Produtos.")
            
        account = self.ledger_repo.get_by_sku(cmd.sku) or InventoryAccount(sku=cmd.sku)
        
        metadata = {
            "supplier": cmd.supplier,
            "expiration_date": cmd.expiration_date,
            "invoice_id": cmd.invoice_id,
            "operator": cmd.operator
        }
        
        account.record_transaction(
            batch_id=cmd.batch_code,
            tx_type=TransactionType.GOODS_RECEIPT,
            quantity=cmd.quantity,
            location_id="DEPOT",
            reference_document=cmd.invoice_id or "MANUAL_RECEIPT",
            metadata=metadata
        )
        self.ledger_repo.save(account)
