#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A/B/C TRANSITION
# SPRINT A005.4 (GATE B.1 & INV000)
# ARCHITECTURE FREEZE & INVENTORY DOMAIN SPECIFICATION
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
    "A/B/C" \
    "A005.4" \
    "Architecture Freeze & Domain Design"

kippe::step 1 ${TOTAL_STEPS} "Consolidating GATE B.1: Architecture Freeze Contract..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/docs/architecture/FROZEN_CONTRACTS.md"
# 🧊 Kippe Platform: Architecture Freeze (Gate B.1)

## 1. Propósito
Este documento declara o congelamento oficial dos contratos de fundação (Program A) e segurança (Program B). Qualquer alteração nas assinaturas públicas, comportamentos esperados ou interfaces listadas abaixo está terminantemente proibida sem a abertura de uma Sprint Corretiva Estrutural, justificativa via ADR e revisão formal de Gate.

## 2. Contratos Públicos Congelados (Frozen Interfaces)

### Core Integration & DI
* \`src/infrastructure/container.py\` -> Classe \`Container\` (Propriedades públicas: \`config\`, \`logger\`, \`product_repository\`, \`operator_repository\`, \`use_case\`, \`auth_use_case\`, \`identity_provider\`).
* \`src/infrastructure/config.py\` -> Classe \`Config\` (Propriedades: \`ENV\`, \`DB_PATH\`, \`LOG_PATH\`, \`HOST\`, \`PORT\`, \`SECRET_KEY\`).

### Observabilidade & Contexto
* \`src/interfaces/logger.py\` -> Protocolo \`Logger\` (Métodos: \`info\`, \`warning\`, \`error\`).
* \`src/interfaces/identity.py\` -> Protocolo \`IdentityProvider\` (Métodos: \`get_current_operator_id\`, \`get_current_operator_role\`).

### Segurança & Persistência Base
* \`src/domain/operator.py\` -> Classe \`Operator\` e regras de criptografia de PIN via hash.
* \`src/infrastructure/identity.py\` -> Classe \`CurrentOperatorResolver\` (Garantia de Implicit Security Context).
* \`src/interfaces/sqlite_operator_repository.py\` -> Classe \`SQLiteOperatorRepository\`.

## 3. Impacto Operacional
O Domínio de Inventário (Program C) herda estes contratos de forma estritamente imutável. Nenhum caso de uso mercantil poderá exigir parâmetros manuais de contexto que violem a resolução implícita provida pelo \`IdentityProvider\`.
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Establishing INV000: Inventory Ubiquitous Language & Domain Design..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/docs/architecture/INV000-INVENTORY-DESIGN.md"
# 📦 Domain Design: PROGRAMA C (Inventory)

## 1. Linguagem Ubíqua (Ubiquitous Language)
* **Mercadoria / Produto (Product):** Elemento master do catálogo mercantil. Possui SKU único, nome descritivo, e unidade de medida padrão (un, kg, lt).
* **SKU (Stock Keeping Unit):** Identificador alfanumérico único e imutável que mapeia o código de barras físico do produto.
* **Lote (Batch/Lot):** Recipiente temporal de estoque físico. Um produto possui N lotes ativos, cada um com seu código identificador, quantidade física e data de validade estrita.
* **Vencimento (Expiration Date):** Data limiar de validade da mercadoria. O sistema proíbe a venda ou movimentação de lotes cuja validade seja menor ou igual à data corrente.
* **Algoritmo FEFO (First Expiring, First Out):** Política de escoamento automático onde as baixas de estoque priorizam o lote com a data de vencimento mais próxima, mitigando perdas financeiras por quebra sanitária.
* **Pick-List (Lista de Separação de Gôndola):** Instrução de retirada gerada sequencialmente pelo algoritmo FEFO, direcionando o repositor ao lote exato no depósito.
* **Ruptura de Estoque (Stockout):** Estado crítico onde a quantidade física total de um SKU atinge zero, impedindo a venda e disparando alertas operacionais.

## 2. Entidades e Agregados (Domain Mapping)
\`\`\`text
[ Product Aggregate Root ]
   └── id: SKU (String, Imutável)
   └── name: Nome (String)
   └── quantity: Quantidade Total Calculada (Integer)
   └── [ Batches Dictionary ]
          └── Key: Batch Code (String)
          └── Value: [ Batch Value Object ]
                 ├── expiration_date: Data (YYYY-MM-DD)
                 └── quantity: Quantidade do Lote (Integer)
\`\`\`

## 3. Invariantes de Negócio (Políticas Inegociáveis)
1. **Invariante de Quantidade Física:** O estoque de um lote ou do produto master jamais poderá ser negativo sob qualquer pretexto operacional.
2. **Invariante de Entrada (Bloqueio de Doca):** É proibida a entrada de lotes vencidos ou que vençam no dia corrente do recebimento.
3. **Invariante de Autoria Nominal:** Nenhuma movimentação de inventário (Entrada/Saída) possui existência anônima. Toda transação deve capturar implicitamente o \`operator_id\` do runtime.
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Running Preflight Script Validation & Entire Regression Suite..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

kippe::step 4 ${TOTAL_STEPS} "Updating Project Executive State to reflect Maturidade Nível 3..."
cat << "KIPPE_HUNK" > ESTADO_PROJETO.md
# 🌐 KIPPE PLATFORM: Institutional Retail Operations

## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 3 (Corporativo) - Contratos Congelados.

## 2. Status Executivo
* **Programa Atual:** PROGRAMA C (Inventory)
* **Gates Transpostos:**
  * [ GATE A - FOUNDATION READY ] ✅
  * [ GATE B - SECURITY READY ] ✅
  * [ GATE B.1 - ARCHITECTURE FREEZE ] ✅
* **Última Entrega:** Sprint A005.4 (Architecture Freeze & Inventory Domain Design - INV000)

## 3. Diretórios e Artefatos Essenciais
* \`docs/architecture/FROZEN_CONTRACTS.md\` -> (Mural de Imutabilidade Estrutural)
* \`docs/architecture/INV000-INVENTORY-DESIGN.md\` -> (Especificação Conceitual do Domínio C)
* \`src/infrastructure/container.py\` -> (Container de Dependências Estabilizado)

## 4. Próxima Ação Requerida
* **Sprint INV001 (Product Catalog & Base Models):** Iniciar a codificação das capacidades mercantis básicas do catálogo. Mapear a estrutura física do Produto estendendo as validações para abarcar Unidades de Medida e Status de Comercialização, amarrando o modelo puro ao repositório de persistência SQLite protegido.
KIPPE_HUNK

kippe::checkpoint_create "017" "1.0.0" "A005.4" "SUCCESS"
kippe::manifest_create "A005.4" "C" "1.0.0" "SUCCESS" "INV001"

kippe::step 5 ${TOTAL_STEPS} "Committing Freeze and Domain Specification..."
git add docs/architecture/FROZEN_CONTRACTS.md docs/architecture/INV000-INVENTORY-DESIGN.md ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_A005.4.json
git commit -m "docs(governance): consolida Gate B.1 Architecture Freeze e especifica o dominio INV000" || true

kippe::banner_finish
kippe::success "Architecture Contracts Frozen. Inventory Domain Specification Consolidated."
echo -e "\n============================================="
echo -e "     [ GATE B.1 - ARCHITECTURE FREEZE ] ✅"
echo -e "     [ PROGRAM C - INVENTORY INITIATED ] 📦"
echo -e "============================================="
echo -e "\nNext Sprint: INV001 (Product Catalog)\n"
exit 0

