#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E016.1: QUERY LAYER REFACTORING (CATALOG DEPENDENCY)
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
kippe::banner_program "E" "E016.1" "Query Layer Refactoring"

kippe::step 1 ${TOTAL_STEPS} "Solidifying InventoryQueryService Cross-Domain Contract..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/application/warehouse/query_service.py"
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.domain.catalog.product import ProductCatalogRepository
from src.domain.warehouse import (
    DualStockView, SmartSheetBuilder, ReplenishmentEngine, 
    TrustScoreEngine, OperationalTruthEngine, DivergenceEngine
)
from src.security.exceptions import NotFoundException

@dataclass(frozen=True)
class InventoryProductView:
    sku: str
    description: str
    brand: str
    category: str
    available_total: int
    depot_balance: int
    store_balance: int
    active_batch: Optional[str]
    primary_supplier: Optional[str]
    last_receipt_date: Optional[str]
    first_expiration_date: Optional[str]
    days_to_expire: Optional[int]
    min_stock: int
    ideal_stock: int
    replenishment_needed: bool
    suggested_quantity: int
    trust_score_percentage: int
    divergence_count: int
    last_divergence: Optional[str]
    operational_risk: float
    recommended_action: str
    action_priority: str
    recent_history: List[str] = field(default_factory=list)

class InventoryQueryService:
    """
    Façade de Leitura (CQRS Read Side).
    Orquestra o Ledger (Event Store) e o Product Catalog para montar uma visão consolidada.
    """
    def __init__(self, ledger_repo: InventoryAccountRepository, catalog_repo: ProductCatalogRepository):
        self.ledger_repo = ledger_repo
        self.catalog_repo = catalog_repo

    def get_sku_view(self, sku: str, min_stock: int = 40, ideal_stock: int = 120) -> InventoryProductView:
        # 1. Recupera o histórico do Ledger
        account = self.ledger_repo.get_by_sku(sku)
        if not account:
            raise NotFoundException(f"SKU {sku} não possui histórico no Ledger.")

        # 2. Enriquecimento via Bounded Context de Catálogo
        product = self.catalog_repo.get_by_sku(sku)
        desc = product.description if product else "Produto Desconhecido"
        brand = product.brand if product else "N/A"
        category = product.category if product else "N/A"

        # 3. Orquestração de Motores do Domínio Warehouse
        sheet = SmartSheetBuilder.build(account, min_stock=min_stock)
        dual_stock = DualStockView.calculate(account.entries, sku)
        replenishment = ReplenishmentEngine.calculate(sheet, min_stock, ideal_stock)
        
        div_events = DivergenceEngine.extract_from_ledger(account.entries)
        trust = TrustScoreEngine.calculate(div_events)
        
        insight = OperationalTruthEngine.evaluate(
            sku=sku, stock_total=dual_stock["total"], divergence_penalty=(1.0 - trust.score),
            trust_score=trust.score, inbound_risk=0.0
        )

        last_div = div_events[-1] if div_events else None
        last_div_desc = f"{last_div.divergence_type} ({last_div.delta})" if last_div else "Nenhuma"

        # Cálculo de Vencimento Seguro
        days_to_expire = None
        exp_date_str = sheet.next_to_expire["expiration"] if sheet.next_to_expire else None
        if exp_date_str and exp_date_str not in ("9999-12-31", "UNKNOWN"):
            try:
                days_to_expire = (datetime.strptime(exp_date_str, "%Y-%m-%d") - datetime.now()).days
            except ValueError:
                pass

        # Histórico Recente
        history = []
        for e in sorted(account.entries, key=lambda x: x.timestamp, reverse=True)[:3]:
            date_short = e.timestamp[5:10].replace("-", "/")
            history.append(f"{date_short} {e.transaction_type.name} {e.quantity:+d}")

        return InventoryProductView(
            sku=sku, description=desc, brand=brand, category=category,
            available_total=dual_stock["total"], depot_balance=dual_stock["depot"], store_balance=dual_stock["store"],
            active_batch=sheet.next_to_expire["id"] if sheet.next_to_expire else "N/A",
            primary_supplier=sheet.last_receipt["supplier"] if sheet.last_receipt else "N/A",
            last_receipt_date=sheet.last_receipt["date"] if sheet.last_receipt else "N/A",
            first_expiration_date=exp_date_str if exp_date_str else "N/A",
            days_to_expire=days_to_expire, min_stock=min_stock, ideal_stock=ideal_stock,
            replenishment_needed=(replenishment is not None), suggested_quantity=replenishment.suggested_quantity if replenishment else 0,
            trust_score_percentage=int(trust.score * 100), divergence_count=trust.divergence_count,
            last_divergence=last_div_desc, operational_risk=insight.priority,
            recommended_action=insight.suggested_action, action_priority=insight.priority,
            recent_history=history
        )
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Updating Presentation and API Tests with the Correct Dependencies..."

# Atualização de teste do QueryService
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/application/warehouse/test_inventory_query_service.py"
import pytest
from src.application.warehouse.query_service import InventoryQueryService
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

def build_scenario(repo):
    account = InventoryAccount(sku="789609890001")
    account.record_transaction("L240621", TransactionType.GOODS_RECEIPT, 148, "DEPOT", "NF-123", 
        {"supplier": "YPE", "expiration_date": "2026-11-15"})
    account.record_transaction("L240621", TransactionType.ADJUSTMENT, -3, "DEPOT", "AUDIT", 
        {"div_type": "UNREGISTERED_WITHDRAWAL", "reason": "Retirada não registrada"})
    repo.save(account)

def test_inventory_query_service_produces_unified_view():
    repo = InMemoryLedgerRepo()
    catalog = InMemoryProductCatalog() # Injeta a dependência necessária
    build_scenario(repo)
    
    service = InventoryQueryService(repo, catalog)
    view = service.get_sku_view("789609890001", min_stock=40, ideal_stock=120)
    
    assert view.sku == "789609890001"
    assert view.description == "Detergente Ypê 500 ml" # Vem do Catálogo
    assert view.available_total == 145
KIPPE_HUNK

# Atualização do Teste da API Router (garantindo injeção do catalog)
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/presentation/api/test_warehouse_router.py"
import pytest
from src.presentation.api.warehouse_router import WarehouseAPIRouter
from src.application.warehouse.query_service import InventoryQueryService
from src.application.warehouse.command_bus import CommandBus
from src.application.warehouse.use_cases.receive_goods import ReceiveGoodsHandler
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.infrastructure.persistence.memory.product_catalog import InMemoryProductCatalog

class InMemoryLedgerRepo(InventoryAccountRepository):
    def __init__(self):
        self.accounts = {}
    def save(self, account: InventoryAccount) -> None:
        self.accounts[account.sku] = account
    def get_by_sku(self, sku: str) -> InventoryAccount:
        return self.accounts.get(sku)

@pytest.fixture
def api_router():
    repo = InMemoryLedgerRepo()
    catalog = InMemoryProductCatalog() # Repositório do Catálogo Mock
    
    # Injeção correta da Façade de Leitura
    query_svc = InventoryQueryService(ledger_repo=repo, catalog_repo=catalog)
    
    bus = CommandBus()
    bus.register(ReceiveGoodsCommand, ReceiveGoodsHandler(repo, catalog))
    
    return WarehouseAPIRouter(query_service=query_svc, command_bus=bus)

def test_api_get_sku_not_found(api_router):
    status, response = api_router.get_sku("999")
    assert status == 404
    assert "não possui histórico" in response["error"]
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Platform Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "113" "1.5.0-platform" "E016.1" "SUCCESS"

echo -e "\n[STATUS] Query Layer Refactoring (E016.1) concluído. Dependências de Catálogo unificadas e consistentes."
exit 0

