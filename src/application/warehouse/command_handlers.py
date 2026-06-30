from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.application.warehouse.commands import (
    ReceiveGoodsCommand, TransferToStoreCommand, RegisterAdjustmentCommand
)
from src.domain.catalog.product import ProductCatalogRepository
from src.security.exceptions import NotFoundException

class WarehouseCommandHandler:
    """
    Orquestrador do Lado de Escrita (Write Side CQRS).
    Recebe comandos puramente de dados, recupera o Agregado, 
    delega a lógica de negócio e persiste os Uncommitted Events.
    """
    def __init__(self, ledger_repo: InventoryAccountRepository, catalog_repo: ProductCatalogRepository):
        self.ledger_repo = ledger_repo
        self.catalog_repo = catalog_repo

    def _get_or_create_account(self, sku: str) -> InventoryAccount:
        # Valida se o produto existe no catálogo mestre antes de movimentar estoque
        if not self.catalog_repo.get_by_sku(sku):
            raise NotFoundException(f"SKU {sku} não encontrado no Catálogo de Produtos.")
            
        account = self.ledger_repo.get_by_sku(sku)
        if not account:
            account = InventoryAccount(sku=sku)
        return account

    def handle_receive_goods(self, cmd: ReceiveGoodsCommand) -> None:
        account = self._get_or_create_account(cmd.sku)
        
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

    def handle_transfer_to_store(self, cmd: TransferToStoreCommand) -> None:
        account = self._get_or_create_account(cmd.sku)
        
        metadata = {"movement_type": "TO_STORE", "operator": cmd.operator}
        
        # Saída do Depósito
        account.record_transaction(cmd.batch_code, TransactionType.TRANSFER_OUT, -cmd.quantity, "DEPOT", "APP_MOV", metadata)
        # Entrada na Loja
        account.record_transaction(cmd.batch_code, TransactionType.TRANSFER_IN, cmd.quantity, "STORE", "APP_MOV", metadata)
        
        self.ledger_repo.save(account)

    def handle_adjustment(self, cmd: RegisterAdjustmentCommand) -> None:
        account = self._get_or_create_account(cmd.sku)
        
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
