#!/bin/bash
# Kippe-Estoque Core | Hotfix: Rollback da Sprint 005 (Scanner CLI)

LOG_DIR="/sdcard/Download/kippe-estoque/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/hotfix-005-${TIMESTAMP}.log"

{
    echo "=== Iniciando Hotfix Rollback Sprint 005 ==="
    
    # 1. Removendo as interfaces alucinadas de hardware
    rm -f src/interfaces/barcode_scanner.py
    rm -f src/interfaces/termux_scanner.py
    rm -f tests/test_scanner.py

    # 2. Restaurando o main.py interativo seguro (CLI pura sem câmera)
    cat << 'EOF' > main.py
import sys
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.use_cases.manage_stock import ManageStockUseCase

def print_menu():
    print("\n" + "="*35)
    print(" KIPPE-ESTOQUE CORE - CLI v1.4")
    print("="*35)
    print("[1] Cadastrar Produto Manual")
    print("[2] Listar Estoque Atual")
    print("[3] Dar Entrada/Saída Manual")
    print("[0] Sair do Sistema")
    print("="*35)

def main():
    repo = SQLiteProductRepository("estoque_producao.db")
    uc = ManageStockUseCase(repository=repo)

    while True:
        print_menu()
        opcao = input("Escolha a operação: ").strip()

        if opcao == '0':
            print("Encerrando Kippe-Estoque Core...")
            sys.exit(0)
            
        elif opcao == '1':
            pid = input("SKU: ").strip()
            nome = input("Nome: ").strip()
            qtd = int(input("Qtd: ").strip() or 0)
            res = uc.create_product(pid, nome, qtd)
            print(f"\n[SUCESSO] {nome} criado!" if res.is_success else f"\n[ERRO] {res.error}")
                
        elif opcao == '2':
            produtos = uc.list_all()
            print("\n--- INVENTÁRIO ---")
            if not produtos: print("Vazio.")
            for p in produtos: print(f"[{p.id}] {p.name} -> {p.quantity} un.")
                
        elif opcao == '3':
            pid = input("SKU: ").strip()
            op = input("Digite '+' para entrada ou '-' para saída: ").strip()
            qtd = int(input("Quantidade: ").strip() or 0)
            if op == '+':
                res = uc.execute_add(pid, qtd)
            elif op == '-':
                res = uc.execute_remove(pid, qtd)
            else:
                print("\n[ERRO] Operador inválido.")
                continue
            print("\n[SUCESSO] Transação efetivada." if res.is_success else f"\n[ERRO] {res.error}")
        else:
            print("\n[ERRO] Opção inexistente.")

if __name__ == "__main__":
    main()
EOF

    # 3. Executando testes para garantir que o Core está seguro
    echo -e "\n[!] Validando integridade do Core pós-rollback...\n"
    python -m pytest tests/ -v
    
} 2>&1 | tee "$LOG_FILE"

FINAL_STATUS=${PIPESTATUS[0]}

if [ $FINAL_STATUS -eq 0 ]; then
    echo -e "\n[OK] Rollback executado. Core validado com sucesso!"
    
    cat << 'EOF' > ESTADO_PROJETO.md
# Estado do Projeto: Kippe-Estoque Core

## 1. Visão Geral e Contexto
* **Objetivo:** Sistema de alta performance (Nível Institucional) para controle logístico.
* **Ambiente de Execução:** Termux (Galaxy A50).
* **Stack:** Python, Pytest, Bash Automation, SQLite.

## 2. Arquitetura Atual (Clean Architecture)
* **Domain:** `Product`, `Result`.
* **Use Cases:** `ManageStockUseCase`.
* **Interfaces (Adapters):** `SQLiteProductRepository` (Persistência).
* **Controller/UI:** CLI operando apenas para testes manuais. Transição iminente para API Flask.

## 3. Arquivos Implementados e Status
* [x] Core e Casos de Uso intactos.
* [x] Rollback de Integração de Câmera CLI efetuado.

## 4. Último Commit Válido Rastreável
* **Hotfix 005:** Rollback do scanner CLI alucinado; Restauração da estabilidade do Core.

## 5. Próximo Passo Imediato
* Criar a camada Web (Flask) integrada ao nosso `ManageStockUseCase` e desenvolver o frontend em HTML5/JS utilizando a biblioteca QuaggaJS (ou html5-qrcode) para viabilizar um leitor de código de barras real, dinâmico e de alta responsividade através do navegador.
EOF

    git add .
    git commit -m "fix(cli): rollback da integracao nativa de hardware para preparar migracao web"
    git push 
fi

