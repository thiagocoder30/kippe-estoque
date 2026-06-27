import sys
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.use_cases.manage_stock import ManageStockUseCase
from src.interfaces.termux_scanner import TermuxBarcodeScanner

def print_menu():
    print("\n" + "="*35)
    print(" KIPPE-ESTOQUE CORE - CLI v1.5")
    print("="*35)
    print("[1] Cadastrar Produto Manual")
    print("[2] Listar Estoque Atual")
    print("[3] Dar Entrada/Saída Manual")
    print("[4] FLUXO RÁPIDO: LER CÓDIGO (CÂMERA)")
    print("[0] Sair do Sistema")
    print("="*35)

def main():
    repo = SQLiteProductRepository("estoque_producao.db")
    uc = ManageStockUseCase(repository=repo)
    scanner = TermuxBarcodeScanner()

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

        elif opcao == '4':
            print("\n>> Inicializando câmera... Aponte para o código de barras.")
            scan_res = scanner.scan()
            
            if not scan_res.is_success:
                print(f"\n[ERRO] {scan_res.error}")
                continue
                
            sku = scan_res.value
            print(f"\n>> LIDO: SKU [{sku}]")
            
            # Automação de Fluxo: Verifica se existe
            produto = repo.get_by_id(sku)
            
            if not produto:
                print(">> Produto não encontrado. Iniciando Cadastro Automático.")
                nome = input(f"Nome para o SKU {sku}: ").strip()
                res = uc.create_product(sku, nome, 0)
                if res.is_success:
                    print(f"[SUCESSO] Produto cadastrado. Saldo: 0.")
                    produto = repo.get_by_id(sku)
                else:
                    print(f"[ERRO] {res.error}")
                    continue
            else:
                print(f">> PRODUTO RECONHECIDO: {produto.name} (Saldo Atual: {produto.quantity} un.)")
                
            acao = input("\nO que deseja fazer? [1] +Entrada | [2] -Saída | [0] Cancelar: ").strip()
            if acao in ('1', '2'):
                try:
                    qtd = int(input("Quantidade: ").strip())
                    if acao == '1':
                        res = uc.execute_add(sku, qtd)
                    else:
                        res = uc.execute_remove(sku, qtd)
                        
                    if res.is_success:
                        print(f"\n[SUCESSO] Estoque de {produto.name} atualizado!")
                    else:
                        print(f"\n[ERRO] {res.error}")
                except ValueError:
                    print("\n[ERRO] Número inválido.")
            else:
                print("\nOperação cancelada.")
        else:
            print("\n[ERRO] Opção inexistente.")

if __name__ == "__main__":
    main()
