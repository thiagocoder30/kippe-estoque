# Estado do Projeto: Kippe-Estoque Core

## 1. Visão Geral e Contexto
* **Objetivo:** Sistema de alta performance para supermercados de bairro (giro rápido).
* **Ambiente de Execução:** Termux (Galaxy A50).
* **Stack:** Python, Pytest, Bash Automation, SQLite, CLI Interativa.

## 2. Arquitetura Atual (Clean Architecture)
* **Domain:** `Product` Entity, `Result` Pattern.
* **Use Cases:** `ManageStockUseCase` orquestrador, operando com Injeção de Dependência.
* **Interfaces (Adapters):** Repositório SQLite idempotente.
* **Controller/UI:** Interface CLI iterativa acoplada no `main.py`.

## 3. Arquivos Implementados e Status
* [x] `src/domain/*` (Entities & Patterns)
* [x] `src/interfaces/*` (SQLite Repository & Protocol)
* [x] `src/use_cases/manage_stock.py` (Orquestração Refatorada)
* [x] `main.py` (CLI REPL Interativa)
* [x] `tests/*` (100% de cobertura nos fluxos críticos)

## 4. Último Commit Válido Rastreável
* **Sprint 004:** Implementação da Injeção de Dependência e CLI principal interativa.

## 5. Próximo Passo Imediato
* Executar o `main.py` localmente no Termux para testar de forma interativa.
* Estruturar a funcionalidade de Leitura de Código de Barras via Câmera do Android integrando ao Termux-API para automatizar a leitura dos SKUs (opcional antes da web) OU avançarmos para construir a camada Web (Flask).

## 6. Bloqueios ou Alucinações Conhecidas
* Nenhum no momento.
