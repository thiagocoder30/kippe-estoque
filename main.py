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
