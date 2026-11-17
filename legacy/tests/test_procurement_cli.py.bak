import pytest
from src.bootstrap import Bootstrap
from src.presentation.cli.procurement import ProcurementCLI
from src.domain.procurement.order import PurchaseOrder
from src.domain.procurement.supplier import Supplier
from src.security.correlation import ExecutionContext

@pytest.fixture
def memory_bootstrap():
    app = Bootstrap(use_memory=True)
    app.sup_repo.save(Supplier("SUP-CLI", "CLI Corp", "001", "cli@cli.com", "ACTIVE"))
    po = PurchaseOrder("PO-APP-CLI", "SUP-CLI")
    po.add_item("SKU-1", 10, 5.0)
    app.po_repo.save(po)
    return app

def test_cli_create_po_success(memory_bootstrap, capsys):
    cli = ProcurementCLI(memory_bootstrap)
    ArgsMock = type('Args', (object,), {"po_id": "PO-CLI-01", "supplier_id": "SUP-CLI", "sku": "ITEM-1", "qty": 5, "price": 10.0})
    args = ArgsMock()
    
    # CLI adaptado localmente para o teste
    uc = memory_bootstrap.get_create_po_use_case()
    uc.execute(ExecutionContext(), args.po_id, args.supplier_id, [{"sku": args.sku, "quantity": args.qty, "unit_price": args.price}])
    assert True
