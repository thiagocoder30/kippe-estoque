#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM B: IDENTITY & SECURITY
# SPRINT SEC000
# SECURITY ARCHITECTURE & THREAT MODEL
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

TOTAL_STEPS=4

kippe::banner_program \
    "B" \
    "SEC000" \
    "Security Architecture Design"

kippe::step 1 ${TOTAL_STEPS} "Drafting Security Architecture Decision Record (ADR-001)..."
cat << 'EOF' > "${KIPPE_ROOT}/docs/architecture/ADR-001-IDENTITY-SECURITY.md"
# ADR 001: Arquitetura de Identidade e Segurança (Programa B)

## 1. Contexto Operacional e Ameaças (Threat Model)
* **Ambiente:** Dispositivo móvel compartilhado no chão de loja (Kiosk Mode/Shared Device).
* **Vetor de Risco:** Operador A loga no sistema, esquece de deslogar, e Operador B realiza movimentações no nome de A (Falso Positivo de Auditoria).
* **Fricção:** Operadores de varejo não têm tempo para digitar senhas alfanuméricas complexas no meio de uma reposição de gôndola.

## 2. Modelo de Autenticação (AuthN)
A plataforma abandonará o modelo corporativo tradicional (E-mail/Senha) em favor de um **Modelo de Frente de Caixa (POS)**:
* **Credencial Primária:** Matrícula Numérica (Ex: 1045) ou Leitura de Crachá (Código de Barras do Operador).
* **Credencial Secundária (Fator de Conhecimento):** PIN de 4 a 6 dígitos (Ex: 123456).
* **Sessão:** Efêmera. O sistema exigirá reautenticação rápida por PIN após X minutos de inatividade para proteger o contexto compartilhado.

## 3. Modelo de Autorização (AuthZ) - RBAC
Role-Based Access Control restrito e codificado no Domínio:
* **OPERADOR:** Pode ler inventário, realizar Entradas e Saídas. NÃO pode excluir registros, modificar histórico ou cadastrar usuários.
* **GERENTE:** Acesso irrestrito. Pode anular transações (compensação reversa), extrair relatórios e redefinir PINs.
* **SISTEMA:** Ator não-humano para rotinas automatizadas (Ex: Backup, Alertas de Ruptura).

## 4. Auditoria Imutável (Audit Trail v2)
A entidade `Transaction` será refatorada. A assinatura do evento deixará de ser anônima.
* **Antes:** `(id, product_id, type, amount, timestamp)`
* **Agora:** `(id, product_id, type, amount, timestamp, operator_id)`
Nenhuma mudança de estado no Core Domain (Motor FEFO) será permitida sem um `operator_id` válido no contexto da requisição.
EOF

kippe::step 2 ${TOTAL_STEPS} "Mapping PROGRAM B Sprints (Security Roadmap)..."
cat << 'EOF' > "${KIPPE_ROOT}/docs/ROADMAP-PROGRAM-B.md"
# 🗺️ Planejamento: PROGRAMA B (Identity & Security)

* **SEC000:** Security Architecture & Threat Model (Atual).
* **SEC001:** Entidade Operator & Repositório de Identidade (Core Domain).
* **SEC002:** Middleware de Autenticação & Sessão JWT (AuthN).
* **SEC003:** Refatoração do Audit Trail para exigir Autoria (Audit V2).
* **SEC004:** UI de Frente de Caixa (Login via PIN/Leitor e Timeout).
* **SEC005:** Sistema de Permissões (RBAC) e Gate de Autorização (AuthZ).
EOF

kippe::step 3 ${TOTAL_STEPS} "Updating ESTADO_PROJETO.md..."
cat << 'EOF' > ESTADO_PROJETO.md
# 🌐 KIPPE PLATFORM: Institutional Retail Operations

## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 2 (Profissional).

## 2. Status Executivo
* **Programa Atual:** PROGRAMA B (Identity & Security)
* **Gate Alvo:** GATE B - Security Ready
* **Última Entrega:** Sprint SEC000 (Security Architecture & Threat Model)

## 3. Diretórios e Artefatos Essenciais
* `data/` - (Fronteira de persistência SQLite)
* `docs/architecture/` - (Manifesto e ADRs de Segurança)
* `src/infrastructure/` - (IoC, Configuração 12-Factor, Logger)
* `reports/logs/` - (Observabilidade e CI)

## 4. Próxima Ação Requerida
* **Sprint SEC001 (Operator Entity & Identity Repository):** Codificar a entidade `Operator` no Core Domain e preparar o banco de dados (`operators` table) para armazenar credenciais com hash criptográfico (bcrypt/sha256), estabelecendo a fundação técnica da identidade no sistema.
EOF

kippe::checkpoint_create \
    "007" \
    "1.0.0" \
    "SEC000" \
    "SUCCESS"

kippe::manifest_create \
    "SEC000" \
    "B" \
    "1.0.0" \
    "SUCCESS" \
    "SEC001"

kippe::step 4 ${TOTAL_STEPS} "Committing Security Design..."
git add docs/architecture/ADR-001-IDENTITY-SECURITY.md docs/ROADMAP-PROGRAM-B.md ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_SEC000.json
git commit -m "docs(security): formaliza arquitetura de identidade POS, RBAC e rastreabilidade nominal (SEC000)" || true

kippe::banner_finish
kippe::success "Security Architecture formalized in repository."
echo -e "\nNext Sprint: SEC001 (Operator Entity)\n"

