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
