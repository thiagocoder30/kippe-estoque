#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E016: REST API ROUTER (PRESENTATION LAYER)
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
kippe::banner_program "E" "E016" "REST API Router (CQRS Exposure)"

# Preparação de Diretórios
mkdir -p "${KIPPE_ROOT}/src/presentation/api"
touch "${KIPPE_ROOT}/src/presentation/api/__init__.py"
mkdir -p "${KIPPE_ROOT}/tests/presentation/api"
touch "${KIPPE_ROOT}/tests/presentation/api/__init__.py"

kippe::step 1 ${TOTAL_STEPS} "Deploying API Router (HTTP to CQRS Translation)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/presentation/api/warehouse_router.py"
import json
from typing import Dict, Any, Tuple
from src.application.warehouse.command_bus import CommandBus
from src.application.warehouse.query_service import InventoryQueryService
from src.application.warehouse.commands import (
    ReceiveGoodsCommand, TransferToStoreCommand, RegisterAdjustmentCommand
)
from src.security.exceptions import NotFoundException, BusinessRuleViolation

class WarehouseAPIRouter:
    """
    Camada de Apresentação REST (Controller/Router).
    Traduz requisições HTTP (JSON/Dicts) para o padrão CQRS da Plataforma.
    """
    def __init__(self, query_service: InventoryQueryService, command_bus: CommandBus):
        self.query_service = query_service
        self.command_bus = command_bus

    # ==========================================
    # READ SIDE (GET)
    # ==========================================
    
    def get_sku(self, sku: str) -> Tuple[int, Dict[str, Any]]:
        """GET /warehouse/api/v1/inventory/{sku}"""
        try:
            view = self.query_service.get_sku_view(sku)
            # Serializa o DTO para JSON-compliant dict
            return 200, {
                "sku": view.sku,
                "description": view.description,
                "balances": {
                    "total": view.available_total,
                    "depot": view.depot_balance,
                    "store": view.store_balance
                },
                "operational_metrics": {
                    "trust_score": view.trust_score_percentage,
                    "risk_level": view.action_priority,
                    "recommended_action": view.recommended_action
                }
            }
        except NotFoundException as e:
            return 404, {"error": str(e)}
        except Exception as e:
            return 500, {"error": "Erro interno do servidor."}

    # ==========================================
    # WRITE SIDE (POST)
    # ==========================================

    def post_receive_goods(self, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """POST /warehouse/api/v1/inventory/receive"""
        try:
            cmd = ReceiveGoodsCommand(
                sku=payload["sku"],
                quantity=payload["quantity"],
                supplier=payload["supplier"],
                batch_code=payload["batch_code"],
                expiration_date=payload.get("expiration_date"),
                invoice_id=payload.get("invoice_id"),
                operator=payload["operator"]
            )
            self.command_bus.dispatch(cmd)
            return 201, {"message": "Recebimento registado com sucesso."}
        except KeyError as e:
            return 400, {"error": f"Campo obrigatório ausente: {str(e)}"}
        except NotFoundException as e:
            return 404, {"error": str(e)}
        except BusinessRuleViolation as e:
            return 422, {"error": str(e)}

    def post_transfer_to_store(self, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """POST /warehouse/api/v1/inventory/transfer"""
        try:
            cmd = TransferToStoreCommand(
                sku=payload["sku"],
                quantity=payload["quantity"],
                batch_code=payload["batch_code"],
                operator=payload["operator"]
            )
            self.command_bus.dispatch(cmd)
            return 201, {"message": "Transferência para loja registada."}
        except Exception as e:
            return 400, {"error": str(e)}
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying API Integration Tests..."

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
    catalog = InMemoryProductCatalog() # Contém SKU 789609890001
    
    query_svc = InventoryQueryService(repo, catalog)
    
    bus = CommandBus()
    bus.register(ReceiveGoodsCommand, ReceiveGoodsHandler(repo, catalog))
    
    return WarehouseAPIRouter(query_service=query_svc, command_bus=bus)

def test_api_get_sku_not_found(api_router):
    status, response = api_router.get_sku("999")
    assert status == 404
    assert "não possui histórico" in response["error"]

def test_api_post_receive_and_get_sku_success(api_router):
    # Simula payload recebido no Body da requisição HTTP POST
    payload = {
        "sku": "789609890001",
        "quantity": 50,
        "supplier": "Distribuidora XPTO",
        "batch_code": "LOTE-API-01",
        "operator": "API_SYS"
    }
    
    # Executa a rota de escrita
    status_post, response_post = api_router.post_receive_goods(payload)
    assert status_post == 201
    assert "sucesso" in response_post["message"]
    
    # Executa a rota de leitura (verificando o CQRS End-to-End)
    status_get, response_get = api_router.get_sku("789609890001")
    assert status_get == 200
    assert response_get["sku"] == "789609890001"
    assert response_get["balances"]["total"] == 50
    assert response_get["operational_metrics"]["trust_score"] == 100

def test_api_post_receive_validation_error(api_router):
    # Faltam campos obrigatórios (ex: operator)
    payload = {"sku": "789609890001", "quantity": 10}
    status, response = api_router.post_receive_goods(payload)
    
    assert status == 400
    assert "Campo obrigatório ausente" in response["error"]
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Platform Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "112" "1.5.0-platform" "E016" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.11" \
    "REST API Integration Layer" \
    "E016 (REST API Router)" \
    "E017 — End-to-End Core Verification" \
    "16/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Sprint E016 (REST API Layer) Concluída. A Plataforma está pronta para o mundo Web/Mobile!"
exit 0

