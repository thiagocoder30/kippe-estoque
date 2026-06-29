#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM C: INVENTORY
# SPRINT INV020: INVENTORY CONSOLIDATION & SIGN-OFF (E2E)
# ============================================================
set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"
# 1. Framework Bootstrap
source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh
# Blindagem de Execução (Fail-Fast)
for fn in kippe::init kippe::validate_script_syntax kippe::test_execute_all kippe::checkpoint_create; do
    if ! declare -F "$fn" >/dev/null; then
        echo "[FATAL] Framework function missing: $fn."
        exit 1
    fi
done
kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR
TOTAL_STEPS=3
kippe::banner_program "C" "INV020" "Inventory Consolidation & Sign-off"
kippe::step 1 ${TOTAL_STEPS} "Deploying Global End-to-End Integration Suite..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/test_program_c_e2e.py"
import pytest
from src.domain.product import Product
from src.domain.batch import Batch
from src.domain.services.inventory_valuation_engine import InventoryValuationEngine
from src.domain.services.order_fulfillment_engine import OrderFulfillmentAllocationEngine
from src.domain.order import OutboundOrder
from src.domain.services.picking_dispatch_engine import PickingDispatchEngine
def test_program_c_complete_logistics_and_financial_flow_e2e():
    """
    Caso de Teste Global de Aceitação:
    Valida a integridade combinada de Recebimento, Valoração,
    Fulfillment All-or-Nothing, Picking, Expedição e Saldo Residual.
    """
    # 1. Configuração do Catálogo e Entrada de Estoque (Lotes com Custo)
    p1 = Product(id="PROD-E2E-1", name="Arroz Integral 1kg", quantity=100)
    p1.batches["L-01"] = Batch(code="L-01", product_id="PROD-E2E-1", quantity=100, expiration_date="2030-12-31", cost_per_unit=4.50)
    
    p2 = Product(id="PROD-E2E-2", name="Feijão Preto 1kg", quantity=200)
    p2.batches["L-02"] = Batch(code="L-02", product_id="PROD-E2E-2", quantity=200, expiration_date="2030-12-31", cost_per_unit=6.00)
    
    catalog = {"PROD-E2E-1": p1, "PROD-E2E-2": p2}
    
    # 2. Auditoria Financeira Inicial (Read Model Valuation)
    val_p1_initial = InventoryValuationEngine.calculate_valuation(p1)
    val_p2_initial = InventoryValuationEngine.calculate_valuation(p2)
    
    assert val_p1_initial.total_value == 450.0   # 100 * 4.50
    assert val_p2_initial.total_value == 1200.0  # 200 * 6.00
    
    # 3. Processamento de Pedido de Venda (Fulfillment Allocation)
    required_items = {"PROD-E2E-1": 20, "PROD-E2E-2": 50}
    fulfillment_res = OrderFulfillmentAllocationEngine.allocate_order(
        order_id="ORD-E2E-999",
        required_items=required_items,
        products_catalog=catalog,
        operator_id="OP-CONSOLIDATOR",
        warehouse_id="CD-CENTRAL"
    )
    
    assert fulfillment_res.is_success is True
    assert p1.quantity == 80
    assert p2.quantity == 150
    
    # 4. Execução do Ciclo Físico de Expedição (Picking & Dispatch)
    outbound_job = OutboundOrder(
        id=fulfillment_res.value["order_id"],
        warehouse_id=fulfillment_res.value["warehouse_id"],
        operator_id=fulfillment_res.value["operator_id"],
        allocated_items=fulfillment_res.value["allocated_items"]
    )
    
    # Avança para Separação
    picking_res = PickingDispatchEngine.start_picking(outbound_job)
    assert picking_res.is_success is True
    assert outbound_job.status == "PICKING"
    
    # Conclui Expedição na Doca de Saída
    dispatch_res = PickingDispatchEngine.confirm_dispatch(outbound_job)
    assert dispatch_res.is_success is True
    assert outbound_job.status == "DISPATCHED"
    assert outbound_job.tracking_code.startswith("TRK-CD-CENTRAL-")
    
    # 5. Auditoria Financeira Final (Verifica se o custo médio e o valor físico derivado estão corretos)
    val_p1_final = InventoryValuationEngine.calculate_valuation(p1)
    val_p2_final = InventoryValuationEngine.calculate_valuation(p2)
    
    assert val_p1_final.total_quantity == 80
    assert val_p1_final.total_value == 80 * 4.50  # 360.0
    
    assert val_p2_final.total_quantity == 150
    assert val_p2_final.total_value == 150 * 6.00 # 900.0
    
    # O Custo Médio Ponderado deve permanecer estável (Invariabilidade Cambial)
    assert val_p1_final.average_cost == 4.50
    assert val_p2_final.average_cost == 6.00
KIPPE_HUNK
kippe::step 2 ${TOTAL_STEPS} "Validating Consolidated Script Syntax via AST Gate..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::step 3 ${TOTAL_STEPS} "Running Full Regression Suite (Signing-off Module)..."
kippe::test_execute_all
# 6. Scorecard Final de Encerramento do Módulo
cat << "SCORECARD" > "${KIPPE_ROOT}/docs/checkpoints/ARCHITECTURE_SCORECARD-INV020.md"
# Architecture Scorecard - Kippe Platform
### Sprint: INV020 - Inventory Consolidation & Sign-off

| Critério | Status | Detalhes |
| :--- | :--- | :--- |
| **Integração E2E** | ✅ | GREEN. Fluxo completo testado e validado em uma única transação lógica. |
| **Isolamento de Camadas** | ✅ | Separação estrita entre Física (Estoque) e Financeira (Valuation) comprovada. |
| **Regressão Global** | ✅ | 100% de passagens na malha acumulada de testes logísticos. |
| **Maturidade Cadastral** | ✅ | Programa C encerrado e declarado estável para consumo institucional. |

SCORECARD
# 7. Checkpoint & 8. Manifest
kippe::checkpoint_create "064" "1.3.0-frozen" "INV020" "SUCCESS"
kippe::manifest_create "INV020" "C" "1.3.0-frozen" "SUCCESS" "COMPLETED"
# Limpeza de resíduos de testes
rm -f data/test_*.db data/test_*.log data/test_*.db-journal 2>/dev/null || true
# 9 a 12. Sincronização e Geração de Manifestos de Produção
kippe::governance_sync \
    "C" \
    "Inventory" \
    "3" \
    "Institucional" \
    "C.5" \
    "Institutional Ready" \
    "INV020 (Inventory Consolidation & Sign-off)" \
    "PROGRAM_COMPLETED" \
    "20/20 Sprints" \
    "STABLE"
exit 0
