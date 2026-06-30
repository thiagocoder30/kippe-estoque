#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E014: COMMAND PATTERN & WRITE ORCHESTRATION (CQRS)
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=3
kippe::banner_program "E" "E014" "Command Pattern (CQRS Write Side)"

kippe::step 1 ${TOTAL_STEPS} "Deploying Commands and Command Handlers (Application Layer)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/application/warehouse/commands.py"
from dataclasses import dataclass
from typing import Optional

# ==========================================
# COMMANDS (Intenções de Escrita Imutáveis)
# ==========================================

@dataclass(frozen=True)
class ReceiveGoodsCommand:
    sku: str
    quantity: int
    supplier: str
    batch_code: str
    expiration_date: Optional[str]
    invoice_id: Optional[str]
    operator: str

@dataclass(frozen=True)
class TransferToStoreCommand:
    sku: str
    quantity: int
    batch_code: str
    operator: str

@dataclass(frozen=True)
class RegisterAdjustmentCommand:
    sku: str
    quantity: int
    batch_code: str
    divergence_type: str
    reason: str
    operator: str
KIPPE_HUNK

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/application/warehouse/command_handlers.py"
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
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Application Tests for Command Handlers..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/application/warehouse/test_command_handlers.py"
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
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Platform Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "110" "1.5.0-platform" "E014" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.9" \
    "CQRS Write Side" \
    "E014 (Command Pattern)" \
    "E015 — Use Cases" \
    "14/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Sprint E014 (Command Pattern) Concluída. Lado de Escrita (Write Model) orquestrado com sucesso!"
exit 0

