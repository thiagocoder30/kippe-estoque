# Estado do Projeto: Controle de Estoque

## 1. Visão Geral e Contexto
* **Objetivo:** Sistema leve de controle de entrada/saída de mercadorias para supermercado de bairro com alto volume de giro.
* **Ambiente de Execução:** Termux no Android (Galaxy A50).
* **Stack:** Python, Flask, SQLite, HTML5/CSS3 puro (Mobile-First).

## 2. Arquitetura do Banco de Dados Atual
* **Tabela `produtos`:** `id` (INTEGER PK), `nome` (TEXT), `quantidade` (INTEGER).

## 3. Arquivos Implementados e Status
* [ ] `app.py` - Script principal contendo as rotas Flask e a interface HTML injetada (Aguardando transposição do MVP).
* [x] `.gitignore` - Configurado para ignorar `__pycache__` e `*.db`.

## 4. Último Commit Válido Rastreável
* **SHA/Mensagem:** N/A (Repositório inicializado).

## 5. Próximo Passo Imediato
* Mover o código do MVP (criado na análise inicial) para o arquivo `app.py` dentro deste novo diretório, realizar o primeiro teste de execução local no Termux e validar as operações de entrada e saída.

## 6. Bloqueios ou Alucinações Conhecidas
* Nenhum até o momento.

