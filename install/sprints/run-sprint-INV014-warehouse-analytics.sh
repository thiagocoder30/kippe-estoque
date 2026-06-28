#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM C: INVENTORY
# SPRINT INV014: WAREHOUSE ANALYTICS (Domain Analytics)
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
TOTAL_STEPS=4
kippe::banner_program "C" "INV014" "Warehouse Analytics"
# Passo 1: Incorporar a melhoria proposta no subsistema de testes para homogeneização de ambiente
kippe::step 1 ${TOTAL_STEPS} "Harmonizing Test Framework Runtime (PYTHONPATH Integration)..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/lib/testing.sh"
#!/usr/bin/env bash
set -Eeuo pipefail
kippe::test_execute_all() {
    echo "  -> Executing Core Regression Suite with Unified PYTHONPATH..."
    # Garante de forma irreversível a localização correta dos pacotes de domínio
    export PYTHONPATH="${KIPPE_ROOT}"
    python3 -m pytest -q "${KIPPE_ROOT}/tests/"
}
KIPPE_HUNK
source "${KIPPE_ROOT}/install/lib/testing.sh"
# 2. Domain Evolution (SafeRefactor / Entity Injection)
kippe::step 2 ${TOTAL_STEPS} "Implementing Warehouse Analytics Domain Service..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/services/warehouse_analytics.py"
from typing import List, Dict
from src.domain.product import Product
class WarehouseAnalytics:
    """
    Domain Service: WarehouseAnalytics
    Fornece métricas analíticas consolidadas sobre a distribuição de estoque e classificação volumétrica.
    """
    @staticmethod
    def calculate_warehouse_utilization(products: List[Product]) -> Dict[str, int]:
        """Agrupa matematicamente o volume físico total de SKUs por planta operacional."""
        utilization = {}
        for p in products:
            for batch in p.batches.values():
                wh = batch.warehouse_id
                utilization[wh] = utilization.get(wh, 0) + batch.quantity
        return utilization
    @staticmethod
    def generate_abc_distribution(products: List[Product]) -> Dict[str, str]:
        """
        Classifica os SKUs em faixas de giro físico (Curva ABC) com base no saldo acumulado.
        A: Top 20% das variações físicas de maior volume.
        B: Próximos 30% em densidade física.
        C: Restantes 50% de cauda longa de giro.
        """
        if not products:
            return {}
            
        # Consolida e ordena do maior para o menor saldo físico
        product_volumes = [(p.id, p.quantity) for p in products]
        product_volumes.sort(key=lambda x: x[1], reverse=True)
        
        total_items = len(product_volumes)
        classification = {}
        
        for index, (pid, _) in enumerate(product_volumes):
            rank = (index + 1) / total_items
            if rank <= 0.20:
                classification[pid] = "A"
            elif rank <= 0.50:
                classification[pid] = "B"
            else:
                classification[pid] = "C"
                
        return classification
KIPPE_HUNK
# 3. Semantic Validator & 4. AST Compile
kippe::step 3 ${TOTAL_STEPS} "Verifying Code Integrity via Semantic and AST Gates..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
# 5. Regression Suite
kippe::step 4 ${TOTAL_STEPS} "Writing and Executing Analytics Verification Suite..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/test_warehouse_analytics.py"
import pytest
from src.domain.product import Product
from src.domain.batch import Batch
from src.domain.services.warehouse_analytics import WarehouseAnalytics
def test_warehouse_utilization_aggregation():
    p1 = Product(id="P1", name="Item A", quantity=50)
    p1.batches["B1"] = Batch(code="B1", product_id="P1", quantity=50, expiration_date="2030-01-01", warehouse_id="WH-CONTAGEM")
    
    p2 = Product(id="P2", name="Item B", quantity=100)
    p2.batches["B2"] = Batch(code="B2", product_id="P2", quantity=70, expiration_date="2030-01-01", warehouse_id="WH-CONTAGEM")
    p2.batches["B3"] = Batch(code="B3", product_id="P2", quantity=30, expiration_date="2030-01-01", warehouse_id="WH-BETIM")
    
    utilization = WarehouseAnalytics.calculate_warehouse_utilization([p1, p2])
    
    assert utilization["WH-CONTAGEM"] == 120
    assert utilization["WH-BETIM"] == 30
def test_abc_distribution_classification():
    products = [
        Product(id="SKU-A", name="Líder de Giro", quantity=500),
        Product(id="SKU-B1", name="Intermediário 1", quantity=200),
        Product(id="SKU-B2", name="Intermediário 2", quantity=150),
        Product(id="SKU-C1", name="Baixo Giro 1", quantity=50),
        Product(id="SKU-C2", name="Baixo Giro 2", quantity=10)
    ]
    
    abc = WarehouseAnalytics.generate_abc_distribution(products)
    
    assert abc["SKU-A"] == "A"
    assert abc["SKU-B1"] == "B"
    assert abc["SKU-C2"] == "C"
KIPPE_HUNK
kippe::test_execute_all
# 6. Architecture Scorecard
cat << "SCORECARD" > "${KIPPE_ROOT}/docs/checkpoints/ARCHITECTURE_SCORECARD-INV014.md"
# Architecture Scorecard - Kippe Platform
### Sprint: INV014 - Warehouse Analytics

| Critério | Status | Detalhes |
| :--- | :--- | :--- |
| **Testes passando** | ✅ | GREEN. Homogeneização do PYTHONPATH atestada. |
| **Agregação Volumétrica** | ✅ | Cálculo exato de volumetria por planta operacional (Warehouses). |
| **Curva ABC Dinâmica** | ✅ | Segmentação percentual de catálogo por densidade física de estoque. |
| **Gate C.4 (Analytics)** | ✅ | Framework de inteligência de armazém formalmente iniciado. |

SCORECARD
# 7. Checkpoint & 8. Manifest
kippe::checkpoint_create "052" "1.3.0-frozen" "INV014" "SUCCESS"
kippe::manifest_create "INV014" "C" "1.3.0-frozen" "SUCCESS" "INV015"
# Limpeza de resíduos transientes
rm -f data/test_*.db data/test_*.log data/test_*.db-journal 2>/dev/null || true
# 9 a 12. Sincronização Compulsória do Estado Permanente (JSON, MD, Roadmap) e Relatório
kippe::governance_sync \
    "C" \
    "Inventory" \
    "2" \
    "Profissional" \
    "C.4" \
    "Analytics" \
    "INV014 (Warehouse Analytics)" \
    "INV015 — Replenishment Engine" \
    "15/20 Sprints" \
    "STABLE"
exit 0
