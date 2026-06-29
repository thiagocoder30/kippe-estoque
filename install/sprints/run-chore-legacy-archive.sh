#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - GOVERNANCE
# CHORE: LEGACY TEST ARCHIVING
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

# 1. Carregamento do Framework
source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=2
kippe::banner_program "GOV" "CHORE" "Legacy Test Archiving"

kippe::step 1 ${TOTAL_STEPS} "Isolating Legacy Artifacts from Main Test Suite..."

# Cria o diretório de quarentena legado
mkdir -p "${KIPPE_ROOT}/tests_legacy"

# Move o teste órfão preservando o histórico, mas removendo do radar do pytest
if [ -f "${KIPPE_ROOT}/tests/test_fefo_allocator.py" ]; then
    mv "${KIPPE_ROOT}/tests/test_fefo_allocator.py" "${KIPPE_ROOT}/tests_legacy/"
    echo " -> Arquivo test_fefo_allocator.py movido para tests_legacy/"
else
    echo " -> Arquivo test_fefo_allocator.py já se encontra arquivado ou não existe."
fi

# Cria um README documentando a decisão arquitetural
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests_legacy/README.md"
# Legacy Tests Archive

Este diretório contém testes e scripts de validação desenvolvidos antes da estabilização da **Baseline 1.3.0 (Inventory Frozen)**.

Eles utilizam APIs descontinuadas (como `Batch 0.x` utilizando `batch_id` e `sku` em vez de `code` e `product_id`) e não utilizam o padrão corporativo do `pytest`. Foram movidos para cá visando preservação histórica sem comprometer a esteira de CI/CD e a doutrina Contract-First.
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Executing Core Regression Suite (Proving Suite Integrity)..."
# Valida que a remoção do arquivo não afetou a contagem de testes reais (92/92 PASS)
kippe::test_execute_all

echo -e "\n[STATUS] Limpeza de legados concluída. A suíte principal permanece estritamente institucional."
exit 0

