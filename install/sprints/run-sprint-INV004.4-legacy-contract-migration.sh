#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM C: INVENTORY
# SPRINT INV004.4: LEGACY FEFO CONTRACT MIGRATION
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
TOTAL_STEPS=5
kippe::banner_program \
    "C" \
    "INV004.4" \
    "Legacy FEFO Contract Migration"
kippe::step 1 ${TOTAL_STEPS} "Deploying Python Refactoring Engine for Legacy Tests..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/sprints/refactor_legacy_tests.py"
import os
import sys
import re
from pathlib import Path
if "KIPPE_ROOT" not in os.environ:
    print("CRITICAL: KIPPE_ROOT environment variable not set.")
    sys.exit(1)
root = Path(os.environ["KIPPE_ROOT"])
test_dir = root / "tests"
if not test_dir.exists():
    print("CRITICAL: Diretório de testes não encontrado.")
    sys.exit(1)
# Expressões Regulares para atualizar os contratos das asserções legadas
# 1. Substitui: assert "LOTE-X" not in p.batches
#    Por:       assert p.batches["LOTE-X"].quantity == 0
regex_deletion = re.compile(r'assert\s+"([^"]+)"\s+not in\s+([a-zA-Z0-9_.]+)\.batches')
# 2. Substitui asserções de contagem cega que quebram com a retenção: len(p.batches)
#    Por contagem de lotes ativos: len([b for b in p.batches.values() if b.quantity > 0])
regex_length = re.compile(r'len\(([a-zA-Z0-9_.]+)\.batches\)')
for test_file in test_dir.glob("test_*.py"):
    content = test_file.read_text(encoding="utf-8")
    original_content = content
    
    # Aplica migração de Contrato de Deleção
    content = regex_deletion.sub(r'assert \2.batches["\1"].quantity == 0', content)
    
    # Aplica migração de Contrato de Contagem
    content = regex_length.sub(r'len([b for b in \1.batches.values() if b.quantity > 0])', content)
    
    # Atualiza o arquivo se houver alterações
    if content != original_content:
        test_file.write_text(content, encoding="utf-8")
        print(f"  -> Contratos legados migrados em: {test_file.name}")
print("  -> Migração de testes concluída com sucesso.")
KIPPE_HUNK
python3 "${KIPPE_ROOT}/install/sprints/refactor_legacy_tests.py"
rm "${KIPPE_ROOT}/install/sprints/refactor_legacy_tests.py"
kippe::step 2 ${TOTAL_STEPS} "Compiling Abstract Syntax Tree (Preflight Gate)..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::step 3 ${TOTAL_STEPS} "Executing Core Suite Regression Validation..."
# O teste de regressão atestará se o conflito de contratos foi pacificado
kippe::test_execute_all
kippe::step 4 ${TOTAL_STEPS} "Generating Architecture Scorecard & Updating Ledger..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/docs/checkpoints/ARCHITECTURE_SCORECARD-INV004.4.md"
# Architecture Scorecard - Kippe Platform
### Sprint: INV004.4 - Legacy FEFO Contract Migration

| Critério | Status | Detalhes / Métricas |
| :--- | :--- | :--- |
| **Testes passando** | ✅ | 100% GREEN. Asserções atualizadas para o contrato de Retenção de Lotes. |
| **Contratos preservados** | ✅ | Domínio intocado; testes espelham o DDD atual. |
| **Cobertura documental** | ✅ | Scorecard atualizado e registrado. |
| **ADR atualizado** | ✅ | Conflito de testes sanado. |
| **Gate impactado** | ❌ | Nenhum. AST Compiler e Preflight aprovados. |
| **Breaking changes** | ❌ | Nenhuma alteração no código de produção. |

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
* **Última Entrega:** Sprint INV004.4 (Legacy FEFO Contract Migration)
## 3. Diretórios e Artefatos Essenciais
* `tests/` -> (Suíte de testes totalmente refatorada e alinhada ao Domain Model)
* `docs/checkpoints/ARCHITECTURE_SCORECARD-INV004.4.md` -> (Métrica de Qualidade)
## 4. Próxima Ação Requerida
* **Sprint INV005 (FIFO Policy Engine):** Com a base de testes expurgada de contratos legados conflitantes e a política FEFO em operação plena, avançaremos para o motor FIFO, viabilizando o gerenciamento logístico de categorias de bens duráveis.
KIPPE_HUNK
kippe::checkpoint_create "028" "1.0.0" "INV004.4" "SUCCESS"
kippe::manifest_create "INV004.4" "C" "1.0.0" "SUCCESS" "INV005"
kippe::step 5 ${TOTAL_STEPS} "Committing Test Contract Alignment..."
git add tests/ ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_INV004.4.json
git commit -m "test(inventory): migra assercoes legadas de delecao para novo contrato de retencao de lotes (INV004.4)" || true
kippe::banner_finish
kippe::success "Legacy Contract Migration complete. Test suite perfectly aligned with Domain invariants."
exit 0
