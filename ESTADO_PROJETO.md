# Estado do Projeto: Kippe-Estoque Core

## 1. Visão Geral e Contexto
* **Objetivo:** Sistema de alta performance (Nível Institucional) para controle logístico de alto volume.
* **Ambiente de Execução:** Termux (Galaxy A50).
* **Stack:** Python, Pytest, Bash Automation, SQLite, Integração Nativa Termux-API.

## 2. Arquitetura Atual (Clean Architecture)
* **Domain:** `Product`, `Result`.
* **Use Cases:** `ManageStockUseCase`.
* **Interfaces (Adapters):** - `SQLiteProductRepository` (Persistência)
  - `TermuxBarcodeScanner` (Integração com Câmera do Dispositivo).
* **Controller/UI:** CLI operando como PDV/Coletor de Dados com suporte a automação de fluxo de leitura.

## 3. Arquivos Implementados e Status
* [x] `src/domain/*` & `src/use_cases/*`
* [x] `src/interfaces/product_repository.py` & `sqlite_repository.py`
* [x] `src/interfaces/barcode_scanner.py` & `termux_scanner.py`
* [x] `main.py` (CLI Avançada com Auto-Detecção de Cadastro via Scanner)
* [x] `tests/*` (Mocks de Hardware isolados da CI local)

## 4. Último Commit Válido Rastreável
* **Sprint 005:** Integração de Hardware via Câmera (Termux-API Scanner).

## 5. Próximo Passo Imediato
* Validar no terreno: Executar o `main.py`, selecionar a opção 4 e utilizar a câmera do Android para ler o código de um produto físico para cadastro/movimentação em tempo real.

## 6. Bloqueios ou Alucinações Conhecidas
* Nenhum. Mocking injetado com sucesso para evitar congelamento nos testes automatizados.
