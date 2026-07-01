#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E018: PLATFORM RELEASE & ARCHITECTURE DOCS
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=2
kippe::banner_program "E" "E018" "Platform Release & Docs"

# Preparação do diretório de documentação
mkdir -p "${KIPPE_ROOT}/docs/architecture"

kippe::step 1 ${TOTAL_STEPS} "Generating KIPPE Warehouse Architecture Manifesto..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/docs/architecture/PROGRAM_E_WAREHOUSE.md"
# 🏛️ KIPPE WMS: Warehouse & Inventory Engine

**Versão:** 1.5.0-platform (Release Candidate)  
**Domínio:** Gestão de Inventário, Confiança Operacional e Event Sourcing.  

---

## 1. A Filosofia (Digital Twin vs. ERP Tradicional)

Os sistemas de inventário tradicionais assumem que a "entrada de dados no sistema" é a verdade absoluta. O KIPPE Warehouse foi desenhado com uma filosofia oposta: **O sistema não confia na operação física por defeito.** Em vez de manter uma única variável de "saldo", o KIPPE atua como um *Digital Twin* (Gémeo Digital) probabilístico. Ele rastreia:
* **Fluxo da Realidade (E008):** Onde está a mercadoria (Depósito vs. Loja).
* **Confiança Operacional (E007):** Quantas vezes o sistema e a prateleira discordaram.
* **Inteligência na Origem (E009):** A qualidade dos lotes e metadados no momento do recebimento.

O objetivo principal é a **Compressão de Decisão (E010)**: transformar dezenas de métricas matemáticas numa única diretiva humana (ex: *OPERAÇÃO NORMAL* ou *AUDITAR ANTES DE COMPRAR*).

---

## 2. Arquitetura (CQRS & Event Sourcing)

O núcleo logístico foi construído com separação estrita entre Escrita e Leitura (CQRS), orquestrado via \`Command Bus\`.

### Lado de Escrita (Write Model)
* **Comandos (Commands):** Intenções imutáveis e puras (\`ReceiveGoodsCommand\`, \`RegisterAdjustmentCommand\`).
* **Command Bus:** Despacha as intenções para Casos de Uso isolados (Princípio Aberto/Fechado).
* **Aggregate Root (\`InventoryAccount\`):** Entidade guardiã das regras de negócio. Valida se a transação é possível.
* **Uncommitted Events:** Padrão de persistência em memória. O Agregado sabe o que acabou de acontecer e emite apenas o diferencial.

### Persistência (Event Store)
* **JSON Lines (JSONL):** O histórico do Ledger é gravado em formato *Append-Only* com complexidade $O(1)$. 
* Não existem \`UPDATES\` ou \`DELETES\` no KIPPE. Todo o erro é corrigido com um novo evento compensatório, garantindo rastreabilidade perfeita.

### Lado de Leitura (Read Model)
* **InventoryQueryService:** A \`Façade\` que orquestra a leitura.
* Reconstrói o estado atual processando sequencialmente a fita de eventos (Ledger) e fundindo os dados com o \`Product Catalog\`.
* Gera o \`InventoryProductView\` (DTO), o único contrato que a Interface de Utilizador (API/CLI) conhece.

---

## 3. Motores de Domínio (Engines)

O KIPPE é composto por motores especializados que rodam na Camada de Aplicação e Domínio:
1. **SmartSheetBuilder:** Reconstrói alertas de validade e lotes.
2. **BalanceEngine:** Projeta o saldo por localização física.
3. **ReplenishmentEngine:** Calcula pontos de encomenda com base no \`Trust Score\`.
4. **DivergenceEngine:** Classifica as anomalias do Event Store.
5. **TrustScoreEngine:** Calcula o nível de degradação da confiança por SKU.
6. **OperationalTruthEngine:** Funde todas as métricas numa decisão tática final.
7. **InventoryAuditService:** Avalia o *compliance* de todo o armazém, caçando SKUs críticos.

---

## 4. Integração (Presentation Layer)

* **Smart CLI:** Ferramenta interativa de linha de comandos para operadores de armazém.
* **REST API Router:** Roteador agnóstico pronto a ser servido via HTTP, consolidando todo o fluxo CQRS.
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Executing Final Governance Alignment..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "117" "1.5.0-platform" "E018" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.13" \
    "Platform Release & Documentation" \
    "E018 (Architecture Docs)" \
    "E019 — System Observability & Telemetry" \
    "18/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Sprint E018 Concluída. Arquitetura oficialmente documentada e KIPPE WMS promovido a Release Candidate."
exit 0

