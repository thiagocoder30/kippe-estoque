# Estado do Projeto: Kippe-Estoque Core

## 1. Visão Geral e Contexto
* **Objetivo:** Sistema de alta performance para supermercados de bairro (giro rápido).
* **Ambiente de Execução:** Termux (Galaxy A50).
* **Stack:** Python, Pytest, Bash Automation, SQLite.

## 2. Arquitetura Atual (Clean Architecture)
* **Domain:** `Product` Entity, `Result` Pattern para resiliência.
* **Use Cases:** `ManageStockUseCase` como orquestrador isolado e idempotente.
* **Interfaces (Adapters):** Repositório base `ProductRepository` com implementação via `SQLiteProductRepository` (Operação de Upsert Atômico).
* **CI/CD:** Pipeline local que gera logs e sincroniza com GitHub na ocorrência de sucesso nos testes.

## 3. Arquivos Implementados e Status
* [x] `src/domain/result.py`
* [x] `src/domain/product.py`
* [x] `src/use_cases/manage_stock.py`
* [x] `src/interfaces/product_repository.py`
* [x] `src/interfaces/sqlite_repository.py`
* [x] `tests/test_domain.py`, `tests/test_use_cases.py`, `tests/test_repository.py`
* [x] `ESTADO_PROJETO.md` - Memória Dinâmica Atualizada (Sprint 003).

## 4. Último Commit Válido Rastreável
* **Sprint 003:** Implementação do Repository Pattern em SQLite.

## 5. Próximo Passo Imediato
* Injetar o repositório (`SQLiteProductRepository`) no caso de uso (`ManageStockUseCase`) e criar a **Camada de Controladores CLI** para que o usuário possa começar a registrar as movimentações diretamente do terminal de forma interativa.

## 6. Bloqueios ou Alucinações Conhecidas
* Nenhum no momento. Testes executando latência sub-100ms.
