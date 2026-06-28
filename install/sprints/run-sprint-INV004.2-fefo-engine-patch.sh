#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM C: INVENTORY
# SPRINT INV004.2: FEFO POLICY ENGINE (Environment Context Patch)
# ============================================================
set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"
source install/lib/bootstrap.sh
source install/lib/testing.sh
source install/lib/validation.sh
kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR
TOTAL_STEPS=6
kippe::banner_program \
    "C" \
    "INV004.2" \
    "FEFO Policy Engine"
kippe::step 1 ${TOTAL_STEPS} "Patching Pipeline: Enforcing PYTHONPATH in testing.sh..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/lib/testing.sh"
#!/usr/bin/env bash
# KIPPE PLATFORM TESTING MODULE
kippe::test_execute_all() {
    echo "  -> Executing Core Regression Suite..."
    export PYTHONPATH="${KIPPE_ROOT}"
    if ! python3 -m pytest -q "${KIPPE_ROOT}/tests/"; then
        kippe::error "Regression Suite FAILED. Broken Domain Contracts detected."
        exit 1
    fi
    echo "  -> Regression Suite: 100% PASSED"
}
KIPPE_HUNK
chmod +x "${KIPPE_ROOT}/install/lib/testing.sh"
kippe::step 2 ${TOTAL_STEPS} "Implementing FEFO Policy Domain Service..."
mkdir -p "${KIPPE_ROOT}/src/domain/services"
touch "${KIPPE_ROOT}/src/domain/services/__init__.py"
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/services/fefo_selector.py"
from typing import List, Dict
from src.domain.batch import Batch
class FEFOSelector:
    """
    Domain Service: First Expiring, First Out (FEFO)
    Encapsula a política institucional de escoamento de perecíveis.
    """
    
    @staticmethod
    def get_eligible_batches(batches: Dict[str, Batch]) -> List[Batch]:
        valid_batches = [
            b for b in batches.values() 
            if b.quantity > 0 and not b.is_expired()
        ]
        
        return sorted(valid_batches, key=lambda b: (b.expiration_date, b.code))
KIPPE_HUNK
kippe::step 3 ${TOTAL_STEPS} "Refactoring Product Aggregate with Environment-Aware Python Engine..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/sprints/refactor_fefo_engine.py"
import os
import sys
from pathlib import Path
# Resolução de rota baseada no contrato de ambiente da plataforma
if "KIPPE_ROOT" not in os.environ:
    print("CRITICAL: KIPPE_ROOT environment variable not set.")
    sys.exit(1)
root = Path(os.environ["KIPPE_ROOT"])
product_path = root / "src/domain/product.py"
content = product_path.read_text(encoding="utf-8")
if "from .services.fefo_selector import FEFOSelector" not in content:
    content = content.replace(
        "from .batch import Batch",
        "from .batch import Batch\nfrom .services.fefo_selector import FEFOSelector"
    )
old_remove = """        remaining = amount
        sorted_batches = sorted(self.batches.items(), key=lambda x: (x[1].expiration_date, x[0]))
        
        for batch_code, batch in sorted_batches:
            if remaining == 0: break
            if batch.quantity <= 0: continue
            if batch.quantity >= remaining:
                batch.quantity -= remaining
                remaining = 0
            else:
                remaining -= batch.quantity
                batch.quantity = 0"""
new_remove = """        eligible_batches = FEFOSelector.get_eligible_batches(self.batches)
        
        available_valid_qty = sum(b.quantity for b in eligible_batches)
        if available_valid_qty < amount:
            return Result.fail("Estoque insuficiente de lotes válidos (vencidos são bloqueados para saída).")
            
        remaining = amount
        for batch in eligible_batches:
            if remaining == 0: break
            if batch.quantity >= remaining:
                batch.quantity -= remaining
                remaining = 0
            else:
                remaining -= batch.quantity
                batch.quantity = 0"""
content = content.replace(old_remove, new_remove)
old_picking = """        sorted_batches = sorted(self.batches.items(), key=lambda x: (x[1].expiration_date, x[0]))
        return [{"lote": k, "validade": v.expiration_date, "qtd_disponivel": v.quantity} for k, v in sorted_batches]"""
new_picking = """        eligible_batches = FEFOSelector.get_eligible_batches(self.batches)
        return [{"lote": b.code, "validade": b.expiration_date, "qtd_disponivel": b.quantity} for b in eligible_batches]"""
content = content.replace(old_picking, new_picking)
product_path.write_text(content, encoding="utf-8")
KIPPE_HUNK
python3 "${KIPPE_ROOT}/install/sprints/refactor_fefo_engine.py"
rm "${KIPPE_ROOT}/install/sprints/refactor_fefo_engine.py"
kippe::step 4 ${TOTAL_STEPS} "Writing Strict Policy Tests for FEFO Engine..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/test_fefo_policy.py"
import pytest
from datetime import datetime, timedelta
from src.domain.product import Product
from src.domain.batch import Batch
def test_fefo_policy_blocks_expired_stock_allocation():
    p = Product(id="SKU-FEFO", name="Iogurte")
    
    ontem = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    amanha = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    p.batches["L-VENCIDO"] = Batch(code="L-VENCIDO", product_id="SKU-FEFO", quantity=10, expiration_date=ontem)
    p.batches["L-VALIDO"] = Batch(code="L-VALIDO", product_id="SKU-FEFO", quantity=5, expiration_date=amanha)
    p.quantity = 15
    
    res = p.remove_stock(10)
    
    assert res.is_success is False
    assert "Estoque insuficiente de lotes válidos" in res.error
    assert p.quantity == 15 
def test_fefo_policy_depletes_correct_batch_sequence():
    p = Product(id="SKU-FEFO-2", name="Leite")
    
    hoje_mais_10 = (datetime.today() + timedelta(days=10)).strftime("%Y-%m-%d")
    hoje_mais_20 = (datetime.today() + timedelta(days=20)).strftime("%Y-%m-%d")
    
    p.batches["L-LONGE"] = Batch(code="L-LONGE", product_id="SKU-FEFO-2", quantity=20, expiration_date=hoje_mais_20)
    p.batches["L-PERTO"] = Batch(code="L-PERTO", product_id="SKU-FEFO-2", quantity=10, expiration_date=hoje_mais_10)
    p.quantity = 30
    
    res = p.remove_stock(15)
    
    assert res.is_success is True
    assert p.batches["L-PERTO"].quantity == 0
    assert p.batches["L-LONGE"].quantity == 15
    assert p.quantity == 15
KIPPE_HUNK
kippe::step 5 ${TOTAL_STEPS} "Executing Core Suite Regression Validation (Gate Enforcement)..."
source "${KIPPE_ROOT}/install/lib/testing.sh"
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all
kippe::step 6 ${TOTAL_STEPS} "Generating Architecture Scorecard & Consolidating Commit..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/docs/checkpoints/ARCHITECTURE_SCORECARD-INV004.2.md"
# Architecture Scorecard - Kippe Platform
### Sprint: INV004.2 - FEFO Policy Engine (Env Context)

| Critério | Status | Detalhes / Métricas |
| :--- | :--- | :--- |
| **Testes passando** | ✅ | Suíte verde. Regras matemáticas de picking (FEFO) consolidadas. |
| **Contratos preservados** | ✅ | Dependência de ambiente (os.environ) aderente aos 12-Factors. |
| **Cobertura documental** | ✅ | Scorecard atualizado. |
| **ADR atualizado** | ✅ | Lógica FEFO delegada e testada de ponta a ponta. |
| **Gate impactado** | ❌ | Nenhum. AST Compiler e Preflight aprovados. |
| **Breaking changes** | ❌ | Assinatura de domínio para \`remove_stock\` permanece a mesma. |

KIPPE_HUNK
cat << "KIPPE_HUNK" > ESTADO_PROJETO.md
# 🌐 KIPPE PLATFORM: Institutional Retail Operations
## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 3 (Corporativo).
## 2. Status Executivo
* **Programa Atual:** PROGRAMA C (Inventory)
* **Gates Transpostos:**
  * [ GATE A - FOUNDATION READY ] ✅
  * [ GATE B - SECURITY READY ] ✅
  * [ GATE B.1 - ARCHITECTURE FREEZE ] ✅
  * [ GATE INFRA - RUNNER HARDENED ] ✅
* **Última Entrega:** Sprint INV004.2 (FEFO Policy Engine)
## 3. Diretórios e Artefatos Essenciais
* `src/domain/services/fefo_selector.py` -> (Políticas de extração de estoque imutáveis)
* `docs/checkpoints/ARCHITECTURE_SCORECARD-INV004.2.md` -> (Métrica de Qualidade e Governança)
## 4. Próxima Ação Requerida
* **Sprint INV005 (FIFO Policy Engine):** Expansão do portfólio de serviços de domínio. Construiremos a mecânica FIFO, habilitando o roteamento da lógica de negócio de acordo com a `classification_rules` das Categorias (ex: perecíveis vão para FEFO, bens duráveis para FIFO).
KIPPE_HUNK
kippe::checkpoint_create "026" "1.0.0" "INV004.2" "SUCCESS"
kippe::manifest_create "INV004.2" "C" "1.0.0" "SUCCESS" "INV005"
git add install/lib/testing.sh src/ tests/ ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_INV004.2.json
git commit -m "feat(inventory): segrega FEFO em Domain Service e utiliza resolucao ambiental (os.environ) (INV004.2)" || true
kippe::banner_finish
kippe::success "FEFO Policy Engine deployed safely via Environment Abstraction."
exit 0
