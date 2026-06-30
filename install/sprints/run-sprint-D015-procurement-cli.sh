#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D015: PROCUREMENT CLI & COMPOSITION ROOT
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

# 1. Carregamento do Framework
source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

# Blindagem de Infraestrutura (Fail-Fast)
for fn in kippe::init kippe::validate_script_syntax kippe::test_execute_all kippe::checkpoint_create; do
    if ! declare -F "$fn" >/dev/null; then
        echo "[FATAL] Framework function missing: $fn. O script foi interrompido."
        exit 1
    fi
done

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=3
kippe::banner_program "D" "D015" "Procurement CLI & Composition Root"

# Preparação de Diretórios
mkdir -p "${KIPPE_ROOT}/src/presentation/cli"
mkdir -p "${KIPPE_ROOT}/tests/presentation"
touch "${KIPPE_ROOT}/src/presentation/__init__.py"
touch "${KIPPE_ROOT}/src/presentation/cli/__init__.py"
touch "${KIPPE_ROOT}/tests/presentation/__init__.py"

kippe::step 1 ${TOTAL_STEPS} "Deploying Composition Root (Bootstrap)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/bootstrap.py"
from src.infrastructure.persistence.json.purchase_order_repository import JsonPurchaseOrderRepository
from src.infrastructure.persistence.json.supplier_repository import JsonSupplierRepository
from src.application.procurement.use_cases import CreatePurchaseOrderUseCase, ApprovePurchaseOrderUseCase

class Bootstrap:
    """
    Composition Root: Instancia a Aplicação.
    Centraliza a Injeção de Dependências (DI). 
    A Camada de Apresentação utiliza o Bootstrap para obter os Casos de Uso
    sem precisar conhecer as implementações de Infraestrutura.
    """
    def __init__(self, use_memory: bool = False):
        if use_memory:
            from src.infrastructure.persistence.in_memory.purchase_order_repository import InMemoryPurchaseOrderRepository
            from src.infrastructure.persistence.in_memory.supplier_repository import InMemorySupplierRepository
            self.po_repo = InMemoryPurchaseOrderRepository()
            self.sup_repo = InMemorySupplierRepository()
        else:
            self.po_repo = JsonPurchaseOrderRepository()
            self.sup_repo = JsonSupplierRepository()

        # Injeção de Casos de Uso (Application Layer)
        self.create_po_uc = CreatePurchaseOrderUseCase(self.po_repo, self.sup_repo)
        self.approve_po_uc = ApprovePurchaseOrderUseCase(self.po_repo)

    def get_create_po_use_case(self) -> CreatePurchaseOrderUseCase:
        return self.create_po_uc

    def get_approve_po_use_case(self) -> ApprovePurchaseOrderUseCase:
        return self.approve_po_uc
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Input Adapters (CLI Controllers)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/presentation/cli/procurement.py"
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
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Deploying Test Suite for Composition Root and CLI..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/presentation/test_procurement_cli.py"
import pytest
from unittest.mock import patch, MagicMock
from src.bootstrap import Bootstrap
from src.presentation.cli.procurement import ProcurementCLI
from src.domain.procurement.order import PurchaseOrder
from src.domain.procurement.supplier import Supplier

@pytest.fixture
def memory_bootstrap():
    """Utiliza implementações em memória para isolar a suíte."""
    app = Bootstrap(use_memory=True)
    # Pré-carrega um Fornecedor Ativo e um Pedido DRAFT para simular o Banco de Dados
    app.sup_repo.save(Supplier("SUP-CLI", "CLI Corp", "001", "cli@cli.com", "ACTIVE"))
    
    po = PurchaseOrder("PO-APP-CLI", "SUP-CLI")
    po.add_item("SKU-1", 10, 5.0)
    app.po_repo.save(po)
    
    return app

def test_bootstrap_initializes_use_cases_correctly(memory_bootstrap):
    create_uc = memory_bootstrap.get_create_po_use_case()
    approve_uc = memory_bootstrap.get_approve_po_use_case()
    
    assert create_uc is not None
    assert approve_uc is not None

def test_cli_create_po_success(memory_bootstrap, capsys):
    cli = ProcurementCLI(memory_bootstrap)
    
    # Mock do objeto 'args' do argparse
    ArgsMock = type('Args', (object,), {"po_id": "PO-CLI-01", "supplier_id": "SUP-CLI", "sku": "ITEM-1", "qty": 5, "price": 10.0})
    args = ArgsMock()
    
    cli.create_po(args)
    
    captured = capsys.readouterr()
    assert "[SUCCESS] Pedido PO-CLI-01 criado com sucesso" in captured.out

def test_cli_create_po_fails_with_invalid_supplier(memory_bootstrap, capsys):
    cli = ProcurementCLI(memory_bootstrap)
    ArgsMock = type('Args', (object,), {"po_id": "PO-CLI-02", "supplier_id": "SUP-GHOST", "sku": "ITEM-1", "qty": 5, "price": 10.0})
    args = ArgsMock()
    
    with pytest.raises(SystemExit) as e:
        cli.create_po(args)
        
    captured = capsys.readouterr()
    assert "[ERROR] Fornecedor SUP-GHOST não encontrado" in captured.out
    assert e.value.code == 1

def test_cli_approve_po_success(memory_bootstrap, capsys):
    cli = ProcurementCLI(memory_bootstrap)
    
    ArgsMock = type('Args', (object,), {"po_id": "PO-APP-CLI"})
    args = ArgsMock()
    
    # É necessário submeter o DRAFT antes de aprovar (Máquina de Estados)
    order = memory_bootstrap.po_repo.get_by_id("PO-APP-CLI")
    order.submit()
    order.start_approval()
    memory_bootstrap.po_repo.save(order)
    
    cli.approve_po(args)
    
    captured = capsys.readouterr()
    assert "[SUCCESS] Pedido PO-APP-CLI aprovado com sucesso" in captured.out
KIPPE_HUNK

kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "079" "1.4.0-procurement" "D015" "SUCCESS"

kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D015 (Procurement CLI & Bootstrap)" \
    "D016 — Security / Hardening" \
    "15/20 Sprints" \
    "STABLE"

mkdir -p /sdcard/Download/kippe_logs
cp data/test_*.log /sdcard/Download/kippe_logs/ 2>/dev/null || true

echo -e "\n[STATUS] CLI Controller & Composition Root (D015) implantados com sucesso."
exit 0

