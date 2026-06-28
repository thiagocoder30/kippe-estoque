#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM C: INVENTORY
# SPRINT INV018: ORDER PICKING & DISPATCH ENGINE
# ============================================================
set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"
# 1. Bootstrap (13-Step Frozen Framework)
source install/lib/bootstrap.sh
source install/lib/testing.sh
source install/lib/validation.sh
kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR
TOTAL_STEPS=3
kippe::banner_program "C" "INV018" "Order Picking & Dispatch"
kippe::step 1 ${TOTAL_STEPS} "Injecting Domain Service: Picking & Dispatch Lifecycle..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/order.py"
from dataclasses import dataclass, field
from typing import Dict
@dataclass
class OutboundOrder:
    """
    Entidade: OutboundOrder
    Representa a ordem de saída física da mercadoria no armazém.
    Estados: ALLOCATED -> PICKING -> DISPATCHED
    """
    id: str
    warehouse_id: str
    operator_id: str
    allocated_items: Dict[str, int]
    status: str = "ALLOCATED"
    tracking_code: str = ""
    def __post_init__(self):
        if not self.id or not self.warehouse_id:
            raise ValueError("ID da Ordem e Armazém são obrigatórios.")
        if not self.allocated_items:
            raise ValueError("A ordem deve conter itens alocados.")
        if self.status not in ["ALLOCATED", "PICKING", "DISPATCHED"]:
            raise ValueError("Status de expedição inválido.")
KIPPE_HUNK
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/services/picking_dispatch_engine.py"
from src.domain.order import OutboundOrder
from src.domain.result import Result
import uuid
class PickingDispatchEngine:
    """
    Domain Service: PickingDispatchEngine
    Controla o avanço operacional da separação física até a expedição e geração de rastreio.
    """
    @staticmethod
    def start_picking(order: OutboundOrder) -> Result[None, str]:
        if order.status != "ALLOCATED":
            return Result.fail("Operação rejeitada: Apenas pedidos ALOCADOS podem iniciar a separação física (Picking).")
        
        order.status = "PICKING"
        return Result.ok(None)
    @staticmethod
    def confirm_dispatch(order: OutboundOrder) -> Result[str, str]:
        if order.status != "PICKING":
            return Result.fail("Operação rejeitada: O pedido deve estar em SEPARAÇÃO (PICKING) para ser expedido.")
        
        order.status = "DISPATCHED"
        # Gera um código de rastreio corporativo único para a doca de saída
        order.tracking_code = f"TRK-{order.warehouse_id}-{uuid.uuid4().hex[:8].upper()}"
        
        return Result.ok(order.tracking_code)
KIPPE_HUNK
# 3. Semantic Validator & 4. AST Compile
kippe::step 2 ${TOTAL_STEPS} "Verifying Code Integrity via Semantic and AST Gates..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
# 5. Regression Suite
kippe::step 3 ${TOTAL_STEPS} "Writing and Executing Picking & Dispatch Test Suite..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/test_picking_dispatch.py"
import pytest
from src.domain.order import OutboundOrder
from src.domain.services.picking_dispatch_engine import PickingDispatchEngine
def test_picking_and_dispatch_lifecycle():
    order = OutboundOrder(
        id="OUT-001", warehouse_id="WH-SP", operator_id="OP-99", 
        allocated_items={"SKU-A": 10, "SKU-B": 5}
    )
    
    assert order.status == "ALLOCATED"
    
    # Inicia Separação
    res1 = PickingDispatchEngine.start_picking(order)
    assert res1.is_success is True
    assert order.status == "PICKING"
    
    # Confirma Expedição
    res2 = PickingDispatchEngine.confirm_dispatch(order)
    assert res2.is_success is True
    assert order.status == "DISPATCHED"
    assert order.tracking_code.startswith("TRK-WH-SP-")
    assert len(order.tracking_code) > 10
def test_dispatch_fails_if_picking_not_started():
    order = OutboundOrder(
        id="OUT-002", warehouse_id="WH-RJ", operator_id="OP-99", 
        allocated_items={"SKU-C": 2}
    )
    
    # Tenta expedir sem passar pela separação
    res = PickingDispatchEngine.confirm_dispatch(order)
    assert res.is_success is False
    assert "deve estar em SEPARAÇÃO" in res.error
def test_start_picking_fails_if_already_dispatched():
    order = OutboundOrder(
        id="OUT-003", warehouse_id="WH-MG", operator_id="OP-99", 
        allocated_items={"SKU-D": 1}, status="DISPATCHED"
    )
    
    res = PickingDispatchEngine.start_picking(order)
    assert res.is_success is False
    assert "Apenas pedidos ALOCADOS" in res.error
KIPPE_HUNK
kippe::test_execute_all
# 6. Architecture Scorecard
cat << "SCORECARD" > "${KIPPE_ROOT}/docs/checkpoints/ARCHITECTURE_SCORECARD-INV018.md"
# Architecture Scorecard - Kippe Platform
### Sprint: INV018 - Order Picking & Dispatch

| Critério | Status | Detalhes |
| :--- | :--- | :--- |
| **Testes passando** | ✅ | GREEN. Ciclo de vida rigoroso de expedição física atestado. |
| **State Machine** | ✅ | Transição unidirecional garantida (ALLOCATED -> PICKING -> DISPATCHED). |
| **Rastreabilidade** | ✅ | Geração automática de Tracking Code (\`TRK-*\`) atrelada ao armazém de origem. |
| **Gate C.5 (Institutional)** | ✅ | Fluxo de saída do inventário completamente mapeado. |

SCORECARD
# 7. Checkpoint & 8. Manifest
kippe::checkpoint_create "057" "1.3.0-frozen" "INV018" "SUCCESS"
kippe::manifest_create "INV018" "C" "1.3.0-frozen" "SUCCESS" "INV019"
# Limpeza de logs
rm -f data/test_*.db data/test_*.log data/test_*.db-journal 2>/dev/null || true
# 9 a 12. Sincronização Compulsória do Estado Permanente
kippe::governance_sync \
    "C" \
    "Inventory" \
    "3" \
    "Institucional" \
    "C.5" \
    "Institutional Ready" \
    "INV018 (Order Picking & Dispatch)" \
    "INV019 — Inventory Valuation (Custo Fixo/Médio)" \
    "19/20 Sprints" \
    "STABLE"
exit 0
