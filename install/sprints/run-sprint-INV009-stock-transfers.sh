#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM C: INVENTORY
# SPRINT INV009: STOCK TRANSFERS (Domain Service)
# ============================================================
set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"
# 1. Bootstrap
source install/lib/bootstrap.sh
source install/lib/testing.sh
source install/lib/validation.sh
kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR
TOTAL_STEPS=6
kippe::banner_program \
    "C" \
    "INV009" \
    "Stock Transfers"
# 2. SafeRefactor (Domain Evolution)
kippe::step 1 ${TOTAL_STEPS} "Upgrading FEFOSelector with Spatial Filtering (Warehouse) via SafeRefactor..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/sprints/refactor_fefo_spatial.py"
import os
import sys
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor
def upgrade_fefo_selector(content: str) -> str:
    # Redefine a inteligência do seletor para isolar lotes por planta geográfica
    old_func = """    @staticmethod
    def get_eligible_batches(batches: Dict[str, Batch]) -> List[Batch]:
        valid_batches = [
            b for b in batches.values() 
            if b.quantity > 0 and not b.is_expired()
        ]
        
        return sorted(valid_batches, key=lambda b: (b.expiration_date, b.code))"""
    new_func = """    @staticmethod
    def get_eligible_batches(batches: Dict[str, Batch], warehouse_id: str = None) -> List[Batch]:
        valid_batches = [
            b for b in batches.values() 
            if b.quantity > 0 and not b.is_expired() and (warehouse_id is None or b.warehouse_id == warehouse_id)
        ]
        return sorted(valid_batches, key=lambda b: (b.expiration_date, b.code))"""
    if old_func in content:
        return content.replace(old_func, new_func)
    return content
try:
    with SafeRefactor("src/domain/services/fefo_selector.py") as sr:
        sr.apply(upgrade_fefo_selector)
except Exception as e:
    print(f"Abortando mutação FEFO: {e}")
    sys.exit(1)
KIPPE_HUNK
python3 "${KIPPE_ROOT}/install/sprints/refactor_fefo_spatial.py"
kippe::step 2 ${TOTAL_STEPS} "Implementing Stock Transfer Engine Domain Service..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/services/stock_transfer_engine.py"
from src.domain.product import Product
from src.domain.result import Result
from src.domain.batch import Batch
from src.domain.services.fefo_selector import FEFOSelector
class StockTransferEngine:
    """
    Domain Service: Stock Transfer Engine
    Orquestra o remanejamento físico de mercadorias entre armazéns da rede.
    Preserva a invariante de massa global do Agregado de Produto.
    """
    @staticmethod
    def execute_transfer(product: Product, amount: int, from_warehouse: str, to_warehouse: str) -> Result[None, str]:
        if product.status == "INATIVO":
            return Result.fail("Operação Rejeitada: SKU suspenso no catálogo.")
        if amount <= 0:
            return Result.fail("A quantidade para transferência deve ser maior que zero.")
        if from_warehouse == to_warehouse:
            return Result.fail("Operação Inválida: Os armazéns de origem e destino devem ser distintos.")
        # 1. Valida saldo disponível local deduzindo reservas logísticas daquela planta
        available_origin = product.get_available_stock_by_warehouse(from_warehouse)
        if available_origin < amount:
            return Result.fail(f"Estoque insuficiente na origem [{from_warehouse}]. Disponível: {available_origin}, Solicitado: {amount}")
        # 2. Coleta os lotes da origem usando ordenação FEFO local
        eligible_batches = FEFOSelector.get_eligible_batches(product.batches, warehouse_id=from_warehouse)
        
        remaining = amount
        for batch in eligible_batches:
            if remaining == 0: break
            
            moved_qty = min(batch.quantity, remaining)
            
            # Débito físico na planta de origem
            batch.quantity -= moved_qty
            
            # Crédito físico na planta de destino
            target_batch_code = f"{batch.code}-TR-{to_warehouse}"
            if target_batch_code in product.batches:
                product.batches[target_batch_code].quantity += moved_qty
            else:
                product.batches[target_batch_code] = Batch(
                    code=target_batch_code,
                    product_id=product.id,
                    quantity=moved_qty,
                    expiration_date=batch.expiration_date,
                    warehouse_id=to_warehouse,
                    location_id="DOCA-TRANSITO",
                    manufacturing_date=batch.manufacturing_date,
                    supplier=batch.supplier,
                    traceability_id=batch.traceability_id
                )
            
            remaining -= moved_qty
        return Result.ok(None)
KIPPE_HUNK
# 3. Semantic Validator & 4. AST Compile
kippe::step 3 ${TOTAL_STEPS} "Verifying Code Integrity via Semantic and AST Gates..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
# 5. Regression Suite
kippe::step 4 ${TOTAL_STEPS} "Writing and Executing Stock Transfer Contract Tests..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/test_stock_transfers.py"
import pytest
from src.domain.product import Product
from src.domain.batch import Batch
from src.domain.services.stock_transfer_engine import StockTransferEngine
def test_stock_transfer_conserves_total_mass_across_warehouses():
    p = Product(id="SKU-MOVE", name="Arroz 5kg", quantity=100)
    b1 = Batch(code="L01", product_id="SKU-MOVE", quantity=100, expiration_date="2032-01-01", warehouse_id="CD-CONTAGEM")
    p.batches["L01"] = b1
    
    # Transfere 40 unidades de Contagem para Betim
    res = StockTransferEngine.execute_transfer(p, 40, "CD-CONTAGEM", "CD-BETIM")
    
    assert res.is_success is True
    assert p.get_stock_by_warehouse("CD-CONTAGEM") == 60
    assert p.get_stock_by_warehouse("CD-BETIM") == 40
    assert p.quantity == 100  # Invariante física de conservação de massa global
def test_stock_transfer_blocks_insufficient_origin_stock():
    p = Product(id="SKU-MOVE-2", name="Feijão", quantity=50)
    b1 = Batch(code="L02", product_id="SKU-MOVE-2", quantity=50, expiration_date="2032-01-01", warehouse_id="CD-CONTAGEM")
    p.batches["L02"] = b1
    
    res = StockTransferEngine.execute_transfer(p, 60, "CD-CONTAGEM", "CD-BETIM")
    assert res.is_success is False
    assert "Estoque insuficiente na origem" in res.error
def test_stock_transfer_prevents_same_warehouse_routing():
    p = Product(id="SKU-MOVE-3", name="Açúcar", quantity=10)
    res = StockTransferEngine.execute_transfer(p, 5, "CD-BETIM", "CD-BETIM")
    assert res.is_success is False
    assert "armazéns de origem e destino devem ser distintos" in res.error
KIPPE_HUNK
kippe::test_execute_all
# 6. Architecture Scorecard
kippe::step 5 ${TOTAL_STEPS} "Emitting Architecture Scorecard..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/docs/checkpoints/ARCHITECTURE_SCORECARD-INV009.md"
# Architecture Scorecard - Kippe Platform
### Sprint: INV009 - Stock Transfers

| Critério | Status | Detalhes / Métricas |
| :--- | :--- | :--- |
| **Testes passando** | ✅ | Suíte verde. Validação estrita do princípio de conservação de massa. |
| **Contratos preservados** | ✅ | \`FEFOSelector\` expandido sem quebrar retrocompatibilidade física. |
| **Garantia de Isolamento** | ✅ | Transferências impedidas de gerar saldos fantasmas ou loops locais. |
| **Gate impactado** | ✅ | Gate C.2 (Warehouse) consolidado com sucesso. |

KIPPE_HUNK
# 7. Checkpoint & 8. Manifest
kippe::checkpoint_create "047" "1.3.0-frozen" "INV009" "SUCCESS"
kippe::manifest_create "INV009" "C" "1.3.0-frozen" "SUCCESS" "INV010"
# Limpeza de scripts temporários de refatoração
rm -f "${KIPPE_ROOT}"/install/sprints/refactor_*.py
rm -f data/test_*.db data/test_*.log data/test_*.db-journal 2>/dev/null || true
# 9 a 12. Sincronização Compulsória do Estado Permanente (JSON, MD, Roadmap) e Relatório
kippe::step 6 ${TOTAL_STEPS} "Synchronizing System State Documents..."
kippe::governance_sync \
    "C" \
    "Inventory" \
    "2" \
    "Profissional" \
    "C.2" \
    "Warehouse" \
    "INV009 (Stock Transfers)" \
    "INV010 — Physical Inventory Adjustments" \
    "10/20 Sprints" \
    "STABLE"
exit 0
