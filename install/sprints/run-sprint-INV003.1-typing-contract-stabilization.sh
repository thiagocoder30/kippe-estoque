#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM C: INVENTORY
# SPRINT INV003.1 (CORRECTIVE SPRINT)
# TYPING CONTRACT STABILIZATION & COMPILER GATE
# ============================================================
set -Eeuo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${ROOT}"
export KIPPE_ROOT="${ROOT}"
export KIPPE_LOG_DIR="${ROOT}/reports/logs"
source install/lib/bootstrap.sh
source install/lib/testing.sh
kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR
TOTAL_STEPS=5
kippe::banner_program \
    "C" \
    "INV003.1" \
    "Typing Contract Stabilization"
kippe::step 1 ${TOTAL_STEPS} "Restoring Typing Contract in Batch Entity..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/batch.py"
from dataclasses import dataclass
from datetime import datetime
from typing import Any
@dataclass
class Batch:
    """
    Entidade: Batch (Domínio de Inventário)
    Garante a integridade física de recipientes temporais de estoque (Lotes).
    """
    code: str  
    product_id: str
    quantity: int
    expiration_date: str  
    manufacturing_date: str = ""  
    supplier: str = "PADRAO"
    status: str = "ATIVO"  
    traceability_id: str = ""
    def __post_init__(self):
        if not self.code or not isinstance(self.code, str) or len(self.code.strip()) == 0:
            raise ValueError("Violação de Invariante: O código do lote é estritamente obrigatório.")
        if not self.product_id or len(self.product_id.strip()) == 0:
            raise ValueError("Violação de Invariante: O lote deve estar atrelado a um SKU válido.")
        if self.quantity < 0:
            raise ValueError("Violação de Invariante: A quantidade do lote não pode ser negativa.")
        
        try:
            datetime.strptime(self.expiration_date, "%Y-%m-%d")
            if self.manufacturing_date:
                datetime.strptime(self.manufacturing_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Violação de Invariante: Formato de data inválido (Use YYYY-MM-DD).")
    def is_expired(self) -> bool:
        exp = datetime.strptime(self.expiration_date, "%Y-%m-%d").date()
        return exp <= datetime.today().date()
    def __getitem__(self, item: str) -> Any:
        if item == 'qty': return self.quantity
        if item == 'exp': return self.expiration_date
        if item == 'supplier': return self.supplier
        if item == 'status': return self.status
        raise KeyError(f"Atributo legado [{item}] indisponível na Entidade Batch.")
KIPPE_HUNK
kippe::step 2 ${TOTAL_STEPS} "Upgrading Preflight Validation with AST Compiler Gate..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/lib/validation.sh"
#!/usr/bin/env bash
# KIPPE PLATFORM PREFLIGHT VALIDATION MODULE
# Prevents malformed scripts and invalid syntax trees from altering the repository state
kippe::validate_script_syntax() {
    local script_path="$1"
    
    echo "  -> Auditing bash syntax: ${script_path}"
    if ! bash -n "${script_path}"; then
        kippe::error "Bash Syntax audit FAILED for ${script_path}. Heredoc anomaly detected."
        exit 1
    fi
    
    echo "  -> Auditing Python AST (Abstract Syntax Tree)..."
    if ! python3 -m compileall -q "${KIPPE_ROOT}/src/" "${KIPPE_ROOT}/app.py" "${KIPPE_ROOT}/tests/"; then
        kippe::error "Python Compile audit FAILED. Syntax, Indentation or Import error detected."
        exit 1
    fi
    
    echo "  -> Preflight Quality Gate: PASSED"
}
KIPPE_HUNK
chmod +x "${KIPPE_ROOT}/install/lib/validation.sh"
kippe::step 3 ${TOTAL_STEPS} "Executing Core Suite Regression Validation (Gate Enforcement)..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all
kippe::step 4 ${TOTAL_STEPS} "Generating Architecture Scorecard & Consolidating Commit..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/docs/checkpoints/ARCHITECTURE_SCORECARD-INV003.1.md"
# Architecture Scorecard - Kippe Platform
### Sprint: INV003.1 - Typing Contract Stabilization

| Critério | Status | Detalhes / Métricas |
| :--- | :--- | :--- |
| **Testes passando** | ✅ | 100% GREEN (Suíte resgatada e validada). |
| **Contratos preservados** | ✅ | Nenhuma alteração lógica; tipagem importada corretamente. |
| **Cobertura documental** | ✅ | ESTADO_PROJETO.md e Scorecard atualizados. |
| **ADR atualizado** | ✅ | Preflight Gate estendido com \`compileall\`. |
| **Gate impactado** | ✅ | Conformidade de infraestrutura restaurada. |
| **Breaking changes** | ❌ | Nenhuma. |
| **Dívida técnica registrada** | ❌ | Falta de importação resolvida e mitigada sistemicamente. |

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
* **Última Entrega:** Sprint INV003.1 (Typing Contract Stabilization)
## 3. Diretórios e Artefatos Essenciais
* `install/lib/validation.sh` -> (Quality Gate com validação AST via compileall)
* `src/domain/batch.py` -> (Entidade com contrato de tipagem estabilizado)
* `docs/checkpoints/ARCHITECTURE_SCORECARD-INV003.1.md` -> (Scorecard de Conformidade)
## 4. Próxima Ação Requerida
* **Sprint INV004 (FEFO Allocation Engine):** Com a estrutura do Lote validada e suportada por um ecossistema de compilação rigoroso, prosseguiremos para a construção do motor mercadológico central da plataforma: a baixa automatizada FEFO (First Expiring, First Out).
KIPPE_HUNK
kippe::checkpoint_create "022" "1.0.0" "INV003.1" "SUCCESS"
kippe::manifest_create "INV003.1" "C" "1.0.0" "SUCCESS" "INV004"
# Limpeza preventiva
rm -f data/test_*.db data/test_*.log data/test_*.db-journal 2>/dev/null || true
# Limpeza de artefatos compilados (.pyc) gerados pelo preflight em runtime
find "${KIPPE_ROOT}" -name "*.pyc" -delete
find "${KIPPE_ROOT}" -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
git add src/domain/batch.py install/lib/validation.sh ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_INV003.1.json
git commit -m "fix(inventory): restaura contrato de tipagem e implementa preflight compiler gate via compileall (INV003.1)" || true
kippe::banner_finish
kippe::success "Typing Contract stabilized. Preflight AST Compiler successfully activated."
exit 0
