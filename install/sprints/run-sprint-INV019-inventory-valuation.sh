#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM C: INVENTORY
# SPRINT INV019: INVENTORY VALUATION (Read Model)
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
TOTAL_STEPS=4
kippe::banner_program "C" "INV019" "Inventory Valuation"
kippe::step 1 ${TOTAL_STEPS} "Applying Non-Destructive Mutations: Batch Cost Extension..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/sprints/patch_batch_cost.py"
import os
import sys
import re
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor
def patch_batch_with_cost(content: str) -> str:
    # Adiciona o atributo financeiro sem quebrar construtores existentes (default 0.0)
    if "cost_per_unit: float" not in content:
        content = content.replace(
            "location_id: str = ''",
            "location_id: str = ''\n    cost_per_unit: float = 0.0"
        )
    return content
def patch_repo_with_cost(content: str) -> str:
    # Garante que o SQLite suporte a leitura/escrita do custo retroativamente
    add_col = '''            cursor = conn.execute("PRAGMA table_info(batches)")
            columns = [info['name'] for info in cursor.fetchall()]
            if 'cost_per_unit' not in columns:
                conn.execute("ALTER TABLE batches ADD COLUMN cost_per_unit REAL NOT NULL DEFAULT 0.0")'''
                
    if "cost_per_unit" not in content:
        content = content.replace(
            "if 'allow_negative_stock' not in columns:",
            add_col + "\n            if 'allow_negative_stock' not in columns:"
        )
        content = content.replace(
            "location_id, warehouse_id)",
            "location_id, warehouse_id, cost_per_unit)"
        )
        content = content.replace(
            "batch.location_id, batch.warehouse_id))",
            "batch.location_id, batch.warehouse_id, float(batch.cost_per_unit)))"
        )
        content = content.replace(
            "status=row_dict['status'], traceability_id=row_dict['traceability_id']",
            "status=row_dict['status'], traceability_id=row_dict['traceability_id'], cost_per_unit=float(row_dict.get('cost_per_unit', 0.0))"
        )
        content = content.replace(
            "status=b_dict['status'], traceability_id=b_dict['traceability_id']",
            "status=b_dict['status'], traceability_id=b_dict['traceability_id'], cost_per_unit=float(b_dict.get('cost_per_unit', 0.0))"
        )
    return content
try:
    with SafeRefactor("src/domain/batch.py") as sr:
        sr.apply(patch_batch_with_cost)
    with SafeRefactor("src/interfaces/sqlite_repository.py") as sr:
        sr.apply(patch_repo_with_cost)
except Exception as e:
    sys.exit(1)
KIPPE_HUNK
python3 "${KIPPE_ROOT}/install/sprints/patch_batch_cost.py"
kippe::step 2 ${TOTAL_STEPS} "Injecting Valuation Domain Entities and Costing Engine..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/valuation.py"
from dataclasses import dataclass, field
from datetime import datetime
@dataclass(frozen=True)
class InventoryValuationResult:
    """
    Entidade: InventoryValuationResult (Read Model Imutável)
    Representa a fotografia financeira do estoque em um dado momento.
    """
    product_id: str
    total_quantity: int
    total_value: float
    average_cost: float
    valuation_method: str
    valuation_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
KIPPE_HUNK
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/services/inventory_valuation_engine.py"
from src.domain.product import Product
from src.domain.valuation import InventoryValuationResult
class InventoryValuationEngine:
    """
    Domain Service: InventoryValuationEngine
    Camada determinística de cálculo financeiro.
    Regra de Ouro: SÓ LÊ. Proibida a mutação do estoque ou dos lotes.
    """
    @staticmethod
    def calculate_valuation(product: Product, method: str = "FIFO") -> InventoryValuationResult:
        if method not in ["FIFO", "AVERAGE"]:
            raise ValueError(f"Método de valoração não suportado: {method}")
        total_qty = 0
        total_value = 0.0
        # Seleciona apenas os lotes físicos reais (ignora lotes virtuais de OVERDRAFT)
        valid_batches = [b for b in product.batches.values() if not b.code.startswith("OVERDRAFT") and b.quantity > 0]
        for batch in valid_batches:
            total_qty += batch.quantity
            total_value += (batch.quantity * batch.cost_per_unit)
        # Trata divisão por zero graciosamente
        average_cost = total_value / total_qty if total_qty > 0 else 0.0
        return InventoryValuationResult(
            product_id=product.id,
            total_quantity=total_qty,
            total_value=total_value,
            average_cost=average_cost,
            valuation_method=method
        )
KIPPE_HUNK
# 3. Semantic Validator & 4. AST Compile
kippe::step 3 ${TOTAL_STEPS} "Verifying Code Integrity via Semantic and AST Gates..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
# 5. Regression Suite
kippe::step 4 ${TOTAL_STEPS} "Writing and Executing Financial Valuation Test Suite..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/test_inventory_valuation.py"
import pytest
from src.domain.product import Product
from src.domain.batch import Batch
from src.domain.services.inventory_valuation_engine import InventoryValuationEngine
def test_valuation_calculates_total_value_and_average_cost():
    p = Product(id="SKU-VAL-1", name="Óleo de Soja", quantity=150)
    
    # Lote antigo, custo menor
    p.batches["L-JAN"] = Batch(code="L-JAN", product_id="SKU-VAL-1", quantity=100, expiration_date="2030-01-01", cost_per_unit=5.00)
    # Lote novo, custo maior (inflação)
    p.batches["L-FEV"] = Batch(code="L-FEV", product_id="SKU-VAL-1", quantity=50, expiration_date="2030-02-01", cost_per_unit=8.00)
    
    # Executa Valuation
    result = InventoryValuationEngine.calculate_valuation(p, method="FIFO")
    
    # Asserções Financeiras
    assert result.total_quantity == 150
    assert result.total_value == (100 * 5.0) + (50 * 8.0) # 500 + 400 = 900
    assert result.average_cost == 900 / 150 # 6.0
    assert result.valuation_method == "FIFO"
def test_valuation_ignores_overdraft_virtual_batches():
    p = Product(id="SKU-VAL-2", name="Açúcar", quantity=0)
    
    # Lote físico com saldo residual
    p.batches["L-1"] = Batch(code="L-1", product_id="SKU-VAL-2", quantity=10, expiration_date="2030-01-01", cost_per_unit=3.0)
    # Lote virtual de descoberto gerado por política de estoque negativo
    p.batches["OVERDRAFT-WH-1"] = Batch(code="OVERDRAFT-WH-1", product_id="SKU-VAL-2", quantity=-10, expiration_date="2099-12-31")
    
    result = InventoryValuationEngine.calculate_valuation(p)
    
    # O Valuation só deve enxergar o custo do lote físico real, ignorando a dívida virtual
    assert result.total_quantity == 10
    assert result.total_value == 30.0
def test_valuation_does_not_mutate_inventory_state():
    p = Product(id="SKU-VAL-3", name="Café", quantity=20)
    p.batches["L-1"] = Batch(code="L-1", product_id="SKU-VAL-3", quantity=20, expiration_date="2030-01-01", cost_per_unit=15.0)
    
    # Fotografia do estado antes do cálculo
    qty_before = p.quantity
    
    _ = InventoryValuationEngine.calculate_valuation(p)
    
    # Garantia do Read Model: O domínio não foi tocado
    assert p.quantity == qty_before
KIPPE_HUNK
kippe::test_execute_all
# 6. Architecture Scorecard
cat << "SCORECARD" > "${KIPPE_ROOT}/docs/checkpoints/ARCHITECTURE_SCORECARD-INV019.md"
# Architecture Scorecard - Kippe Platform
### Sprint: INV019 - Inventory Valuation Engine

| Critério | Status | Detalhes |
| :--- | :--- | :--- |
| **Testes passando** | ✅ | GREEN. Valorações calculadas perfeitamente. |
| **Isolamento de Estado** | ✅ | \`InventoryValuationResult\` atua como um Read Model projetado e isolado. |
| **Integridade Operacional** | ✅ | Cálculo ignora sumariamente lotes de \`OVERDRAFT\` virtuais. |
| **Gate C.5 (Institutional)** | ✅ | Ponte arquitetural para o futuro Módulo Financeiro estabelecida. |

SCORECARD
# 7. Checkpoint & 8. Manifest
kippe::checkpoint_create "058" "1.3.0-frozen" "INV019" "SUCCESS"
kippe::manifest_create "INV019" "C" "1.3.0-frozen" "SUCCESS" "INV020"
# Limpeza de logs e patches
rm -f "${KIPPE_ROOT}"/install/sprints/patch_*.py
rm -f data/test_*.db data/test_*.log data/test_*.db-journal 2>/dev/null || true
# 9 a 12. Sincronização Compulsória do Estado Permanente
kippe::governance_sync \
    "C" \
    "Inventory" \
    "3" \
    "Institucional" \
    "C.5" \
    "Institutional Ready" \
    "INV019 (Inventory Valuation)" \
    "INV020 — Inventory Consolidation & Sign-off" \
    "20/20 Sprints" \
    "STABLE"
exit 0
