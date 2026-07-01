#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E015: USE CASES & COMMAND BUS (DISPATCHER)
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

TOTAL_STEPS=4
kippe::banner_program "E" "E015" "Use Cases & Command Bus"

# Preparação de Diretórios
mkdir -p "${KIPPE_ROOT}/src/application/warehouse/use_cases"
touch "${KIPPE_ROOT}/src/application/warehouse/use_cases/__init__.py"

kippe::step 1 ${TOTAL_STEPS} "Deploying Command Bus (Dispatcher)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/application/warehouse/command_bus.py"
from typing import Type, Dict, Any

class CommandBus:
    """
    Orquestrador central de Comandos.
    Desacopla a emissão do comando da sua execução física,
    garantindo que cada intenção tenha um único Handler responsável.
    """
    def __init__(self):
        self._handlers: Dict[Type, Any] = {}

    def register(self, command_type: Type, handler: Any) -> None:
        self._handlers[command_type] = handler

    def dispatch(self, command: Any) -> None:
        handler = self._handlers.get(type(command))
        if not handler:
            raise ValueError(f"Nenhum handler registado para o comando: {type(command).__name__}")
        handler.execute(command)
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Refactoring Monolithic Handler into Independent Use Cases..."

# Caso de Uso 1: Recebimento de Mercadorias
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/application/warehouse/use_cases/receive_goods.py"
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
KIPPE_HUNK

# Caso de Uso 2: Transferência para Loja
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/application/warehouse/use_cases/transfer_to_store.py"
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
KIPPE_HUNK

# Caso de Uso 3: Registo de Ajuste (Divergências)
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/application/warehouse/use_cases/register_adjustment.py"
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
KIPPE_HUNK

# Limpa o antigo Handler monolítico
rm -f "${KIPPE_ROOT}/src/application/warehouse/command_handlers.py"

kippe::step 3 ${TOTAL_STEPS} "Updating Test Suite to validate isolated Use Cases via Command Bus..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/application/warehouse/test_command_handlers.py"
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
KIPPE_HUNK

kippe::step 4 ${TOTAL_STEPS} "Verifying Syntax and Executing Platform Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "111" "1.5.0-platform" "E015" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.10" \
    "CQRS Use Cases" \
    "E015 (Command Bus)" \
    "E016 — REST API" \
    "15/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Sprint E015 (Use Cases & Command Bus) Concluída. Arquitetura aderente ao Princípio Aberto/Fechado (OCP)!"
exit 0

