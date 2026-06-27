# 📦 Kippe-Estoque Core: Master Roadmap Institucional

## 1. Visão Geral
* **Objetivo:** Controle logístico WMS, prevenção de rupturas e falhas sanitárias.
* **Arquitetura:** Clean Architecture, Algoritmo FEFO no Core, RESTful API (Flask).
* **Ambiente:** Termux Server (Galaxy A50) + Client HTML5.

## 2. Roadmap de Engenharia (Sprints)
* [x] Sprints 001 a 007: Core O(1), Repositório SQLite, API Web, Scanner HTML5 e Audit Trail.

### FASE 4: Governança & Segurança Logística (Atual)
* [x] **Sprint 008 (V2):** FEFO Institucional. Adicionado controle estrito de `Lotes` e Aba de Reposição (Pick-List), gerando rotas autônomas de retirada de depósito baseadas na data de vencimento.
* [ ] **Sprint 009:** Autenticação de Operador (Sistema de PIN numérico no Audit Trail).

### FASE 5: Inteligência de Negócio & Relatórios (A Fazer)
* [ ] **Sprint 010:** Dashboard Analítico (Alerta de ruptura de estoque).
* [ ] **Sprint 011:** Exportação de Dados (CSV das movimentações).
