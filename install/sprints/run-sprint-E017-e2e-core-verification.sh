#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E017: END-TO-END CORE VERIFICATION
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
kippe::banner_program "E" "E017" "End-to-End Core Verification"

# Preparação de Diretórios
mkdir -p "${KIPPE_ROOT}/tests/integration"
touch "${KIPPE_ROOT}/tests/integration/__init__.py"

kippe::step 1 ${TOTAL_STEPS} "Completing API Router with Adjustment Endpoint..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/presentation/api/warehouse_router.py"
import json
import traceback
from typing import Dict, Any, Tuple
from src.application.warehouse.command_bus import CommandBus
from src.application.warehouse.query_service import InventoryQueryService
from src.application.warehouse.commands import (
    ReceiveGoodsCommand, TransferToStoreCommand, RegisterAdjustmentCommand
)
from src.security.exceptions import NotFoundException, BusinessRuleViolation

class WarehouseAPIRouter:
    def __init__(self, query_service: InventoryQueryService, command_bus: CommandBus):
        self.query_service = query_service
        self.command_bus = command_bus

    # ==========================================
    # READ SIDE (GET)
    # ==========================================
    
    def get_sku(self, sku: str) -> Tuple[int, Dict[str, Any]]:
        try:
            view = self.query_service.get_sku_view(sku)
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
            print("\n\033[91m[API INTERNAL ERROR]\033[0m")
            traceback.print_exc()
            return 500, {"error": "Erro interno do servidor.", "details": str(e)}

    # ==========================================
    # WRITE SIDE (POST)
    # ==========================================

    def post_receive_goods(self, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        try:
            cmd = ReceiveGoodsCommand(
                sku=payload["sku"], quantity=payload["quantity"], supplier=payload["supplier"],
                batch_code=payload["batch_code"], expiration_date=payload.get("expiration_date"),
                invoice_id=payload.get("invoice_id"), operator=payload["operator"]
            )
            self.command_bus.dispatch(cmd)
            return 201, {"message": "Recebimento registado com sucesso."}
        except KeyError as e:
            return 400, {"error": f"Campo obrigatório ausente: {str(e)}"}
        except NotFoundException as e:
            return 404, {"error": str(e)}
        except BusinessRuleViolation as e:
            return 422, {"error": str(e)}
        except Exception as e:
            print("\n\033[91m[API INTERNAL ERROR]\033[0m")
            traceback.print_exc()
            return 500, {"error": "Erro interno do servidor."}

    def post_transfer_to_store(self, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        try:
            cmd = TransferToStoreCommand(
                sku=payload["sku"], quantity=payload["quantity"],
                batch_code=payload["batch_code"], operator=payload["operator"]
            )
            self.command_bus.dispatch(cmd)
            return 201, {"message": "Transferência para loja registada."}
        except Exception as e:
            return 400, {"error": str(e)}

    def post_register_adjustment(self, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        try:
            cmd = RegisterAdjustmentCommand(
                sku=payload["sku"], quantity=payload["quantity"],
                batch_code=payload["batch_code"], divergence_type=payload["divergence_type"],
                reason=payload["reason"], operator=payload["operator"]
            )
            self.command_bus.dispatch(cmd)
            return 201, {"message": "Divergência/Ajuste registado com sucesso."}
        except Exception as e:
            return 400, {"error": str(e)}
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying End-to-End Core Verification Test..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/integration/test_e2e_core_flow.py"
import pytest
from src.presentation.api.warehouse_router import WarehouseAPIRouter
from src.application.warehouse.query_service import InventoryQueryService
from src.application.warehouse.command_bus import CommandBus
from src.application.warehouse.commands import ReceiveGoodsCommand, TransferToStoreCommand, RegisterAdjustmentCommand
from src.application.warehouse.use_cases.receive_goods import ReceiveGoodsHandler
from src.application.warehouse.use_cases.transfer_to_store import TransferToStoreHandler
from src.application.warehouse.use_cases.register_adjustment import RegisterAdjustmentHandler
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
def e2e_system():
    repo = InMemoryLedgerRepo()
    catalog = InMemoryProductCatalog() # Contém SKU 789609890001
    
    query_svc = InventoryQueryService(ledger_repo=repo, catalog_repo=catalog)
    
    bus = CommandBus()
    bus.register(ReceiveGoodsCommand, ReceiveGoodsHandler(repo, catalog))
    bus.register(TransferToStoreCommand, TransferToStoreHandler(repo, catalog))
    bus.register(RegisterAdjustmentCommand, RegisterAdjustmentHandler(repo, catalog))
    
    return WarehouseAPIRouter(query_service=query_svc, command_bus=bus)

def test_holy_trinity_operational_flow_e2e(e2e_system):
    """
    Testa o ciclo de vida completo:
    Entrada -> Movimentação -> Divergência -> Verificação de Risco
    Garantindo que a camada REST orquestra o CQRS perfeitamente.
    """
    sku = "789609890001"
    
    # 1. ENTRADA DE MERCADORIA
    status, _ = e2e_system.post_receive_goods({
        "sku": sku, "quantity": 200, "supplier": "Indústria Ypê",
        "batch_code": "L26-MAX", "expiration_date": "2026-12-31",
        "invoice_id": "NF-999", "operator": "Thiago"
    })
    assert status == 201

    # 2. MOVIMENTAÇÃO PARA LOJA
    status, _ = e2e_system.post_transfer_to_store({
        "sku": sku, "quantity": 40, "batch_code": "L26-MAX", "operator": "Repositor A"
    })
    assert status == 201

    # 3. DIVERGÊNCIA OPERACIONAL (Retirada não registada detetada em contagem)
    status, _ = e2e_system.post_register_adjustment({
        "sku": sku, "quantity": -5, "batch_code": "L26-MAX", 
        "divergence_type": "UNREGISTERED_WITHDRAWAL", 
        "reason": "Produto não encontrado na prateleira", "operator": "Auditor B"
    })
    assert status == 201

    # 4. VERIFICAÇÃO FINAL (O Momento da Verdade do Read Model)
    status, view_json = e2e_system.get_sku(sku)
    assert status == 200
    
    balances = view_json["balances"]
    metrics = view_json["operational_metrics"]
    
    # Validação de Matemática de Saldo
    assert balances["total"] == 195  # 200 recebidos - 5 perdidos
    assert balances["store"] == 40   # 40 enviados
    assert balances["depot"] == 155  # 200 recebidos - 40 enviados - 5 perdidos
    
    # Validação de Qualidade / Confiança
    assert metrics["trust_score"] < 100 # Foi penalizado pela divergência
    assert metrics["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"] 
    # Com 5 unidades de volume de ajuste, a matemática do domínio reagiu
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing End-to-End Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "116" "1.5.0-platform" "E017" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.12" \
    "End-to-End Core Verification" \
    "E017 (E2E Holy Trinity Flow)" \
    "E018 — Platform Release & Docs" \
    "17/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] End-to-End Core Verification (E017) concluída! O motor logístico da KIPPE está homologado."
exit 0

