import sys
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.use_cases.manage_stock import ManageStockUseCase

def print_menu():
    print("\n" + "="*30)
    print(" KIPPE-ESTOQUE CORE - CLI")
    print("="*30)
    print("[1] Cadastrar Produto")
    print("[2] Listar Produtos")
    print("[3] Dar Entrada no Estoque (+)")
    print("[4] Dar Saída no Estoque (-)")
    print("[0] Sair")
    print("="*30)

def main():
    repo = SQLiteProductRepository("estoque_producao.db")
    uc = ManageStockUseCase(repository=repo)

    while True:
        print_menu()
        opcao = input("Escolha uma opção: ").strip()

        if opcao == '0':
            print("Encerrando sistema...")
            sys.exit(0)
            
        elif opcao == '1':
            pid = input("Código do Produto (SKU): ").strip()
            nome = input("Nome do Produto: ").strip()
            try:
                qtd = int(input("Quantidade Inicial: ").strip())
                res = uc.create_product(pid, nome, qtd)
                if res.is_success:
                    print(f"\n[SUCESSO] Produto {nome} cadastrado!")
                else:
                    print(f"\n[ERRO] {res.error}")
            except ValueError:
                print("\n[ERRO] Quantidade deve ser um número inteiro.")
                
        elif opcao == '2':
            produtos = uc.list_all()
            print("\n--- ESTOQUE ATUAL ---")
            if not produtos:
                print("Nenhum produto cadastrado.")
            for p in produtos:
                print(f"[{p.id}] {p.name} - Saldo: {p.quantity} un.")
                
        elif opcao == '3':
            pid = input("Código do Produto (SKU): ").strip()
            try:
                qtd = int(input("Quantidade para Entrada: ").strip())
                res = uc.execute_add(pid, qtd)
                if res.is_success:
                    print(f"\n[SUCESSO] Entrada de {qtd} unidades efetuada.")
                else:
                    print(f"\n[ERRO] {res.error}")
            except ValueError:
                print("\n[ERRO] Quantidade inválida.")

        elif opcao == '4':
            pid = input("Código do Produto (SKU): ").strip()
            try:
                qtd = int(input("Quantidade para Saída: ").strip())
                res = uc.execute_remove(pid, qtd)
                if res.is_success:
                    print(f"\n[SUCESSO] Baixa de {qtd} unidades efetuada.")
                else:
                    print(f"\n[ERRO] {res.error}")
            except ValueError:
                print("\n[ERRO] Quantidade inválida.")
        else:
            print("\n[ERRO] Opção inválida.")

if __name__ == "__main__":
    main()
