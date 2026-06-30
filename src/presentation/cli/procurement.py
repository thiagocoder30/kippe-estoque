import argparse
import sys
from src.bootstrap import Bootstrap

class ProcurementCLI:
    """
    Input Adapter: Interface de Linha de Comando (CLI).
    Extrai argumentos do utilizador e delega a execução para a camada de Application.
    Nenhuma regra de negócio reside aqui.
    """
    def __init__(self, bootstrap: Bootstrap):
        self.bootstrap = bootstrap

    def create_po(self, args):
        uc = self.bootstrap.get_create_po_use_case()
        items = [{"sku": args.sku, "quantity": args.qty, "unit_price": args.price}]
        
        try:
            order = uc.execute(args.po_id, args.supplier_id, items)
            print(f"[SUCCESS] Pedido {order.id} criado com sucesso (Status: {order.status}).")
        except ValueError as e:
            print(f"[ERROR] {e}")
            sys.exit(1)

    def approve_po(self, args):
        uc = self.bootstrap.get_approve_po_use_case()
        try:
            uc.execute(args.po_id)
            print(f"[SUCCESS] Pedido {args.po_id} aprovado com sucesso.")
        except ValueError as e:
            print(f"[ERROR] {e}")
            sys.exit(1)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KIPPE Platform - Procurement CLI")
    subparsers = parser.add_subparsers(dest="command", help="Comandos Disponiveis")

    # Comando: create-po
    parser_create = subparsers.add_parser("create-po", help="Criar novo Pedido de Compra")
    parser_create.add_argument("--po-id", required=True, help="ID do Pedido")
    parser_create.add_argument("--supplier-id", required=True, help="ID do Fornecedor")
    parser_create.add_argument("--sku", required=True, help="SKU do Item")
    parser_create.add_argument("--qty", required=True, type=int, help="Quantidade")
    parser_create.add_argument("--price", required=True, type=float, help="Preço Unitário")

    # Comando: approve-po
    parser_approve = subparsers.add_parser("approve-po", help="Aprovar um Pedido Existente")
    parser_approve.add_argument("--po-id", required=True, help="ID do Pedido")

    return parser

def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Inicia a aplicação usando repositórios JSON (Produção)
    app = Bootstrap(use_memory=False)
    cli = ProcurementCLI(app)

    if args.command == "create-po":
        cli.create_po(args)
    elif args.command == "approve-po":
        cli.approve_po(args)

if __name__ == "__main__":
    main()
