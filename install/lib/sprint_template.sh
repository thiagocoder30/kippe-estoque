#!/usr/bin/env bash
# KIPPE PLATFORM - STANDARD SPRINT TEMPLATE
# Este template impõe os 13 passos do Framework Frozen.
set -Eeuo pipefail
export KIPPE_ROOT="\${KIPPE_ROOT:-\$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "\${KIPPE_ROOT}"
# 1. Bootstrap
source install/lib/bootstrap.sh
source install/lib/testing.sh
source install/lib/validation.sh
kippe::init
kippe::init_environment
trap 'kippe::on_error \${LINENO}' ERR
TOTAL_STEPS=3
kippe::banner_program "C" "INVXXX" "Nome da Sprint"
# 2. SafeRefactor (Domain Evolution)
kippe::step 1 \${TOTAL_STEPS} "Aplicando Mutações de Domínio..."
# [Injetar Scripts de SafeRefactor Aqui]
# 3. Semantic Validator & 4. AST Compile
kippe::step 2 \${TOTAL_STEPS} "Validando Semântica e Sintaxe..."
kippe::validate_script_syntax "\${BASH_SOURCE[0]}"
# 5. Regression Suite
kippe::step 3 \${TOTAL_STEPS} "Executando Regressão Completa..."
kippe::test_execute_all
# 6. Architecture Scorecard
cat << "SCORECARD" > "\${KIPPE_ROOT}/docs/checkpoints/ARCHITECTURE_SCORECARD-INVXXX.md"
# Scorecard INVXXX

| Critério | Status | Detalhes |
| :--- | :--- | :--- |
| **Testes passando** | ✅ | 100% GREEN. |

SCORECARD
# 7. Checkpoint & 8. Manifest
kippe::checkpoint_create "045" "1.3.0-frozen" "INVXXX" "SUCCESS"
kippe::manifest_create "INVXXX" "C" "1.3.0-frozen" "SUCCESS" "INVYYY"
# 9 a 12. Atualização Automática de Estados (JSON, MD, Roadmap) e Sugestão
kippe::governance_sync \
    "C" "Inventory" \
    "2" "Profissional" \
    "C.2" "Warehouse" \
    "INVXXX" "INVYYY — Proxima Sprint" \
    "X/20 Sprints" "STABLE"
# 13. Commit Sugerido (Saída no console)
echo -e "\n[AÇÃO REQUERIDA] Execute o commit para imutabilidade:"
echo -e 'git add -A && git commit -m "feat(inventory): descricao (INVXXX)"'
exit 0
