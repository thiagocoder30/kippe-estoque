#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A: FOUNDATION
# SPRINT A000.2
# GOVERNANCE & ARCHITECTURAL MANIFESTO
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

TOTAL_STEPS=5

kippe::banner_program \
    "A" \
    "A000.2" \
    "Governance & Manifesto"

kippe::step 1 ${TOTAL_STEPS} "Generating Architectural Manifesto..."
cat << 'EOF' > docs/architecture/MANIFESTO.md
# 🏛️ Kippe Platform: Manifesto Arquitetural

## Princípio Fundamental
A Kippe Platform é uma plataforma institucional de operações para o varejo (Institutional Retail Operations Platform). Toda decisão técnica deve suportar resiliência, escalabilidade e altíssima disponibilidade no chão de loja.

## O que este projeto NUNCA poderá se tornar?
Este documento é a nossa fronteira de integridade. Sob nenhuma circunstância o projeto violará as seguintes regras:

1. **Nunca será um "CRUD" de estoque:** A plataforma lida com eventos temporais, fluxos imutáveis (Audit Trails) e algoritmos logísticos (FEFO/FIFO). O banco de dados reflete o estado consequente, não o estado inicial.
2. **Nunca terá regras de negócio espalhadas por Controllers ou UIs:** O *Core Domain* (Regras da Empresa) será sempre blindado e agnóstico a frameworks, operando em complexidade estrutural O(1) sempre que possível.
3. **Nunca crescerá sem documentação estruturada:** Sprints não existem no vácuo. Toda mudança estrutural exige atualização do Estado do Projeto e geração de artefatos de arquitetura (ADRs).
4. **Nunca adicionará funcionalidades sem justificativa arquitetural:** Cada linha de código deve pertencer a um Domínio de Negócio (Programa) claro e resolver uma capacidade real da operação.
5. **Nunca aceitará dívida técnica de forma silenciosa:** Exceções ignoradas e falhas silenciosas são terminantemente proibidas. O padrão `Result/Either` é lei. Qualquer débito assumido estrategicamente deve ser registrado.

> *"Nenhuma decisão será tomada apenas para resolver o problema de hoje; toda implementação deverá continuar coerente quando o sistema tiver centenas de Sprints e novos módulos."*
EOF

kippe::step 2 ${TOTAL_STEPS} "Establishing Capability-Driven Roadmap..."
cat << 'EOF' > docs/ROADMAP.md
# 🗺️ Master Roadmap: Kippe Platform

## Estrutura de Maturidade
* **Nível 1:** Funcional
* **Nível 2:** Profissional
* **Nível 3:** Corporativo
* **Nível 4:** Enterprise
* **Nível 5:** Institucional

---

## Estrutura de Programas e Gates

### PROGRAMA A: Foundation
*Objetivo: Construir o núcleo imutável da plataforma.*
* **Sprints:** A000 (Governança) a A009 (Release Candidate)
* **Gate de Saída:** [ GATE A - Foundation Ready ]

### PROGRAMA B: Identity & Security
*Objetivo: Garantir rastreabilidade, RBAC e compliance (LGPD).*
* **Sprints:** SEC001 (Usuários) a SEC009 (Hardening)
* **Gate de Saída:** [ GATE B - Security Ready ]

### PROGRAMA C: Inventory
*Objetivo: WMS completo de alta performance (Motor Logístico).*
* **Sprints:** INV001 (Produtos) a INV020 (Finalização)
* **Gate de Saída:** [ GATE C - Inventory Ready ]

### Futuros Programas Mapeados
* **PROGRAMA D:** Procurement (Compras e Fornecedores)
* **PROGRAMA E:** Sales (Frente de Caixa / PDV)
* **PROGRAMA F:** Analytics (Inteligência de Negócio e KPIs)
* **PROGRAMA G:** Integrations (APIs Externas, ERPs)
* **PROGRAMA H:** Infrastructure (Resiliência e Nuvem)
* **PROGRAMA I:** Artificial Intelligence (Previsão de Demanda e Análise Comportamental)
EOF

kippe::step 3 ${TOTAL_STEPS} "Updating ESTADO_PROJETO.md as Single Source of Truth..."
cat << 'EOF' > ESTADO_PROJETO.md
# 🌐 KIPPE PLATFORM: Institutional Retail Operations

## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 1 (Funcional) caminhando para Nível 2.

## 2. Status Executivo
* **Programa Atual:** PROGRAMA A (Foundation)
* **Gate Alvo:** GATE A - Foundation Ready
* **Última Entrega:** Sprint A000.2 (Governance & Manifesto)

## 3. Diretórios e Artefatos Essenciais
* `docs/architecture/MANIFESTO.md` - (Constituição do Sistema)
* `docs/ROADMAP.md` - (Planejamento de Capacidades)
* `install/sprints/` - (Motor de Integração Contínua)
* `reports/logs/` - (Rastreabilidade de Instalação Local)

## 4. Próxima Ação Requerida
* **Sprint A001 (Arquitetura):** Integrar o módulo de Testes (`install/tests/`) ao framework de fundação, garantindo que toda Sprint entregue já venha acompanhada de sua validação automática, pavimentando o caminho sólido para o Gate A.
EOF

kippe::step 4 ${TOTAL_STEPS} "Generating Checkpoint & Manifest..."
kippe::checkpoint_create \
    "001" \
    "1.0.0" \
    "A000.2" \
    "SUCCESS"

kippe::manifest_create \
    "A000.2" \
    "A" \
    "1.0.0" \
    "SUCCESS" \
    "A001"

kippe::step 5 ${TOTAL_STEPS} "Committing Governance Artifacts..."
# CORREÇÃO: Apontando o git add para o local exato onde o manifest_create gera o arquivo
git add docs/architecture/MANIFESTO.md docs/ROADMAP.md ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_A000.2.json
git commit -m "docs(governance): implementa manifesto arquitetural, roadmap por capacidades e estrutura de gates" || true

kippe::banner_finish
kippe::success "Governance & Manifesto successfully established."
echo -e "\nNext Sprint: A001 (Architecture & Testing Framework)\n"

