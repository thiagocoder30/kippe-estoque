#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E016.2: REST API TEST COVERAGE RESTORATION
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

TOTAL_STEPS=2
kippe::banner_program "E" "E016.2" "REST API Test Coverage Restoration"

kippe::step 1 ${TOTAL_STEPS} "Restoring complete API test suite with proper cross-domain imports..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/presentation/api/test_warehouse_router.py"
import pytest
from src.presentation.api.warehouse_router import WarehouseAPIRouter
from src.application.warehouse.query_service import InventoryQueryService
from src.application.warehouse.command_bus import CommandBus
from src.application.warehouse.commands import ReceiveGoodsCommand
from src.application.warehouse.use_cases.receive_goods import ReceiveGoodsHandler
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.domain.warehouse.ledger import InventoryAccount
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
    catalog = InMemoryProductCatalog() # Injeção do Bounded Context do Catálogo
    
    query_svc = InventoryQueryService(ledger_repo=repo, catalog_repo=catalog)
    
    bus = CommandBus()
    bus.register(ReceiveGoodsCommand, ReceiveGoodsHandler(repo, catalog))
    
    return WarehouseAPIRouter(query_service=query_svc, command_bus=bus)

def test_api_get_sku_not_found(api_router):
    status, response = api_router.get_sku("999")
    assert status == 404
    assert "não possui histórico" in response["error"]

def test_api_post_receive_and_get_sku_success(api_router):
    # Payload simulando o corpo de uma requisição HTTP POST inbound
    payload = {
        "sku": "789609890001",
        "quantity": 50,
        "supplier": "Distribuidora XPTO",
        "batch_code": "LOTE-API-01",
        "operator": "API_SYS"
    }
    
    status_post, response_post = api_router.post_receive_goods(payload)
    assert status_post == 201
    assert "sucesso" in response_post["message"]
    
    # Validação do CQRS read-side sincronizado com o write-side
    status_get, response_get = api_router.get_sku("789609890001")
    assert status_get == 200
    assert response_get["sku"] == "789609890001"
    assert response_get["balances"]["total"] == 50
    assert response_get["operational_metrics"]["trust_score"] == 100

def test_api_post_receive_validation_error(api_router):
    # Payload corrompido com ausência de campo obrigatório
    payload = {"sku": "789609890001", "quantity": 10}
    status, response = api_router.post_receive_goods(payload)
    
    assert status == 400
    assert "Campo obrigatório ausente" in response["error"]
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Platform Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto de Governança
kippe::checkpoint_create "114" "1.5.0-platform" "E016.2" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.11" \
    "REST API Integration Layer" \
    "E016.2 (Test Suite Fixed)" \
    "E017 — End-to-End Core Verification" \
    "16/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Cobertura de testes da API REST totalmente restaurada e integrada com sucesso."
exit 0

