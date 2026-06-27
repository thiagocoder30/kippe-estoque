#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A: FOUNDATION
# SPRINT A001
# ARCHITECTURE & TESTING FRAMEWORK
# ============================================================

set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${ROOT}"

export KIPPE_ROOT="${ROOT}"
export KIPPE_LOG_DIR="${ROOT}/reports/logs"

source install/lib/bootstrap.sh

kippe::init
kippe::init_environment

trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=6

kippe::banner_program \
    "A" \
    "A001" \
    "Architecture & Testing Framework"

kippe::step 1 ${TOTAL_STEPS} "Building Testing Module (testing.sh)..."
cat << 'EOF' > install/lib/testing.sh
#!/usr/bin/env bash
# KIPPE PLATFORM TESTING MODULE
# Orchestrates automated validation to prevent regressions.

kippe::test_environment() {
    echo "  -> Validating test dependencies..."
    if ! command -v python &> /dev/null; then
        kippe::error "Python environment not found. Halting."
    fi
    if ! python -m pytest --version &> /dev/null; then
        kippe::error "Pytest not found. Halting."
    fi
}

kippe::test_run_core() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local test_log="${KIPPE_LOG_DIR}/test-core-${timestamp}.log"
    
    echo "  -> Running Core Domain Test Suite..."
    
    if [[ -d "${KIPPE_ROOT}/tests" ]]; then
        if ! python -m pytest "${KIPPE_ROOT}/tests/" -v > "${test_log}" 2>&1; then
            cat "${test_log}"
            kippe::error "Core Domain Tests FAILED. Architecture violation detected. Rollback required."
        fi
        echo "  -> Core Domain Tests PASSED. Log saved to reports/logs."
    else
        echo "  -> No tests/ directory found yet. Skipping core domain validation."
    fi
}

kippe::test_execute_all() {
    echo "[TEST SUITE INITIATED]"
    kippe::test_environment
    kippe::test_run_core
    echo "[TEST SUITE COMPLETED SUCCESSFULLY]"
}
EOF
chmod +x install/lib/testing.sh

kippe::step 2 ${TOTAL_STEPS} "Injecting Testing Module into Bootstrap..."
# Adiciona o carregamento automático do testing.sh no bootstrap se ainda não existir
if ! grep -q "source.*testing.sh" install/lib/bootstrap.sh; then
    echo 'source "${KIPPE_ROOT}/install/lib/testing.sh"' >> install/lib/bootstrap.sh
fi

kippe::step 3 ${TOTAL_STEPS} "Validating Integration (Dry Run)..."
# Carrega manualmente para a execução atual
source install/lib/testing.sh
kippe::test_execute_all

kippe::step 4 ${TOTAL_STEPS} "Updating ESTADO_PROJETO.md..."
cat << 'EOF' > ESTADO_PROJETO.md
# 🌐 KIPPE PLATFORM: Institutional Retail Operations

## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 1 (Funcional).

## 2. Status Executivo
* **Programa Atual:** PROGRAMA A (Foundation)
* **Gate Alvo:** GATE A - Foundation Ready
* **Última Entrega:** Sprint A001 (Architecture & Testing Framework)

## 3. Diretórios e Artefatos Essenciais
* `docs/architecture/MANIFESTO.md` - (Constituição do Sistema)
* `docs/ROADMAP.md` - (Planejamento de Capacidades)
* `install/sprints/` - (Motor de Integração Contínua)
* `install/lib/testing.sh` - (Orquestrador de Qualidade Integrada)
* `reports/logs/` - (Rastreabilidade de Execução Local)

## 4. Próxima Ação Requerida
* **Sprint A002 (Refatoração Core):** Integrar e refatorar o código-fonte desenvolvido na prototipação inicial para dentro das diretrizes estritas do nosso novo framework estrutural.
EOF

kippe::step 5 ${TOTAL_STEPS} "Generating Checkpoint & Manifest..."
kippe::checkpoint_create \
    "002" \
    "1.0.0" \
    "A001" \
    "SUCCESS"

kippe::manifest_create \
    "A001" \
    "A" \
    "1.0.0" \
    "SUCCESS" \
    "A002"

kippe::step 6 ${TOTAL_STEPS} "Committing Testing Framework Artifacts..."
git add install/lib/bootstrap.sh install/lib/testing.sh install/sprints/run-sprint-A001-architecture-testing.sh ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_A001.json
git commit -m "test(framework): implementa suite de validacao automatizada e integra ao bootstrap do sistema" || true

kippe::banner_finish
kippe::success "Testing Framework successfully installed and integrated."
EOF

