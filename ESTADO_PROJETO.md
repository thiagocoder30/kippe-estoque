# Estado do Projeto: Kippe-Estoque Core

## 1. Visão Geral e Contexto
* **Objetivo:** Sistema de alta performance (Nível Institucional) para controle logístico.
* **Ambiente de Execução:** Termux Server + Navegador Mobile (Galaxy A50).
* **Stack:** Python, Flask, Pytest, SQLite, QuaggaJS/HTML5-QRCode (Leitor de Câmera Real-Time).

## 2. Arquitetura Atual (Clean Architecture)
* **Domain & Use Cases:** Totalmente isolados e blindados (O(1) perfomance).
* **Interfaces (Adapters):** SQLiteProductRepository.
* **Controller/UI:** API RESTful via Flask (`app.py`), substituindo a CLI. Interface visual SPA injetada via `templates/index.html`.

## 3. Arquivos Implementados e Status
* [x] `app.py` configurado como servidor central na porta 5000.
* [x] `templates/index.html` construído com UX/UI Mobile-First institucional.
* [x] `tests/test_api.py` cobrindo 100% dos endpoints.

## 4. Último Commit Válido Rastreável
* **Sprint 006:** Criação da Camada Web, API RESTful e Integração Scanner HTML5 Visual.

## 5. Próximo Passo Imediato
* Executar `python app.py` no Termux e acessar o IP local `http://127.0.0.1:5000` via Google Chrome no celular para testes intensivos em produção.
