#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A: FOUNDATION
# SPRINT A002
# CORE REFACTORING & TOPOLOGY ALIGNMENT
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

TOTAL_STEPS=7

kippe::banner_program \
    "A" \
    "A002" \
    "Core Refactoring & Topology"

kippe::step 1 ${TOTAL_STEPS} "Purging Ghost Files and Anomalies..."
# Remove o arquivo gerado por erro de digitação identificado na auditoria
rm -f "${KIPPE_ROOT}/vim"

kippe::step 2 ${TOTAL_STEPS} "Archiving MVP Legacy Sprints..."
mkdir -p "${KIPPE_ROOT}/install/sprints/archive_mvp"
# Move as Sprints de 001 a 008 e utilitários antigos para o arquivo
mv "${KIPPE_ROOT}"/install/sprints/run-sprint-00*.sh "${KIPPE_ROOT}/install/sprints/archive_mvp/" 2>/dev/null || true
mv "${KIPPE_ROOT}"/install/sprints/run-hotfix-*.sh "${KIPPE_ROOT}/install/sprints/archive_mvp/" 2>/dev/null || true
mv "${KIPPE_ROOT}"/install/sprints/run-roadmap-update.sh "${KIPPE_ROOT}/install/sprints/archive_mvp/" 2>/dev/null || true

kippe::step 3 ${TOTAL_STEPS} "Isolating Database Layer (Data Folder)..."
mkdir -p "${KIPPE_ROOT}/data"
# Move o banco de produção se existir
if [[ -f "${KIPPE_ROOT}/estoque_producao.db" ]]; then
    mv "${KIPPE_ROOT}/estoque_producao.db" "${KIPPE_ROOT}/data/"
fi

# Proteção para que o banco físico não suba pro GitHub
if ! grep -q "data/\*.db" "${KIPPE_ROOT}/.gitignore" 2>/dev/null; then
    echo "data/*.db" >> "${KIPPE_ROOT}/.gitignore"
fi

kippe::step 4 ${TOTAL_STEPS} "Refactoring Source Paths (Repository & App)..."
# Atualiza o repositório para usar a pasta data/ como padrão
sed -i 's|db_path: str = "estoque_producao.db"|db_path: str = "data/estoque_producao.db"|g' "${KIPPE_ROOT}/src/interfaces/sqlite_repository.py"

# Atualiza a injeção de dependência na inicialização do Flask
sed -i 's|repo = SQLiteProductRepository("estoque_producao.db")|repo = SQLiteProductRepository("data/estoque_producao.db")|g' "${KIPPE_ROOT}/app.py"

# Atualiza os caminhos temporários dos testes para não sujarem a raiz
sed -i 's|db_path = "test_estoque.db"|db_path = "data/test_estoque.db"|g' "${KIPPE_ROOT}/tests/test_repository.py" 2>/dev/null || true
sed -i 's|os.remove(db_path)|if os.path.exists(db_path): os.remove(db_path)|g' "${KIPPE_ROOT}/tests/test_repository.py" 2>/dev/null || true

sed -i 's|db_path = "test_usecase.db"|db_path = "data/test_usecase.db"|g' "${KIPPE_ROOT}/tests/test_use_cases.py" 2>/dev/null || true
sed -i 's|db = "test_audit.db"|db = "data/test_audit.db"|g' "${KIPPE_ROOT}/tests/test_audit.py" 2>/dev/null || true

sed -i 's|"test_api_flask.db"|"data/test_api_flask.db"|g' "${KIPPE_ROOT}/tests/test_api.py" 2>/dev/null || true

kippe::step 5 ${TOTAL_STEPS} "Validating Architecture Integrity (Testing Framework)..."
# Invocando a validação automatizada instituída na Sprint A001
kippe::test_execute_all

kippe::step 6 ${TOTAL_STEPS} "Updating ESTADO_PROJETO.md..."
cat << 'EOF' > ESTADO_PROJETO.md
# 🌐 KIPPE PLATFORM: Institutional Retail Operations

## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 1 (Funcional).

## 2. Status Executivo
* **Programa Atual:** PROGRAMA A (Foundation)
* **Gate Alvo:** GATE A - Foundation Ready
* **Última Entrega:** Sprint A002 (Core Refactoring & Topology Alignment)

## 3. Diretórios e Artefatos Essenciais
* `data/` - (Fronteira de isolamento de persistência de dados físicos)
* `docs/architecture/MANIFESTO.md` - (Constituição do Sistema)
* `docs/ROADMAP.md` - (Planejamento de Capacidades)
* `install/sprints/` - (Motor de Integração Contínua limpo e arquivado)
* `install/lib/testing.sh` - (Orquestrador de Qualidade Integrada)

## 4. Próxima Ação Requerida
* **Sprint A003 (Eventos/Observabilidade):** Implementar um mecanismo de log unificado na aplicação Python. Isso garantirá que todas as rejeições da regra de negócio (ex: tentativa de dar baixa sem lote, FEFO violation) sejam gravadas em log institucional (`reports/logs/app.log`), saindo da caixa-preta e facilitando o trace da operação.
EOF

kippe::step 7 ${TOTAL_STEPS} "Generating Manifest and Committing..."
kippe::checkpoint_create \
    "003" \
    "1.0.0" \
    "A002" \
    "SUCCESS"

kippe::manifest_create \
    "A002" \
    "A" \
    "1.0.0" \
    "SUCCESS" \
    "A003"

git add data/ .gitignore app.py src/interfaces/sqlite_repository.py tests/ ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_A002.json install/sprints/
git commit -m "refactor(core): realinha topologia, expurga artefatos legados e integra testes ao CI" || true

kippe::banner_finish
kippe::success "Core Refactoring & Topology perfectly aligned."
echo -e "\nNext Sprint: A003 (Eventos & Observabilidade)\n"

