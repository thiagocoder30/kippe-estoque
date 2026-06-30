import pytest
from src.application.procurement.use_cases import CreatePurchaseOrderUseCase, ApprovePurchaseOrderUseCase
from src.infrastructure.persistence.in_memory.purchase_order_repository import InMemoryPurchaseOrderRepository
from src.infrastructure.persistence.in_memory.supplier_repository import InMemorySupplierRepository
from src.domain.procurement.supplier import Supplier
from src.domain.procurement.order import PurchaseOrder

@pytest.fixture
def setup_repos():
    sup_repo = InMemorySupplierRepository()
    po_repo = InMemoryPurchaseOrderRepository()
    
    # Prepara estado inicial
    sup_repo.save(Supplier("SUP-100", "Ativo Corp", "001", "a@a.com", "ACTIVE"))
    sup_repo.save(Supplier("SUP-999", "Blocked Corp", "002", "b@b.com", "BLOCKED"))
    
    # Prepara PO para os testes de aprovação
    po = PurchaseOrder("PO-APP", "SUP-100", status="UNDER_APPROVAL")
    po.add_item("SKU-Z", 10, 5.0)
    # Bypass protection to mock state
    object.__setattr__(po, 'status', 'UNDER_APPROVAL')
    po_repo.save(po)
    
    return sup_repo, po_repo

def test_create_purchase_order_use_case(setup_repos):
    sup_repo, po_repo = setup_repos
    uc = CreatePurchaseOrderUseCase(po_repo, sup_repo)
    
    items = [{"sku": "SKU-A", "quantity": 100, "unit_price": 2.5}]
    order = uc.execute("PO-001", "SUP-100", items)
    
    assert order.id == "PO-001"
    assert order.status == "DRAFT"
    
    # Verifica persistência
    saved = po_repo.get_by_id("PO-001")
    assert saved is not None
    assert len(saved.items) == 1

def test_create_po_fails_if_supplier_not_found(setup_repos):
    sup_repo, po_repo = setup_repos
    uc = CreatePurchaseOrderUseCase(po_repo, sup_repo)
    
    with pytest.raises(ValueError, match="não encontrado"):
        uc.execute("PO-002", "SUP-GHOST", [{"sku": "A", "quantity": 1, "unit_price": 1.0}])

def test_create_po_fails_if_supplier_blocked(setup_repos):
    sup_repo, po_repo = setup_repos
    uc = CreatePurchaseOrderUseCase(po_repo, sup_repo)
    
    with pytest.raises(ValueError, match="não está ativo para novas compras"):
        uc.execute("PO-003", "SUP-999", [{"sku": "B", "quantity": 1, "unit_price": 1.0}])

def test_approve_purchase_order_use_case(setup_repos):
    _, po_repo = setup_repos
    uc = ApprovePurchaseOrderUseCase(po_repo)
    
    uc.execute("PO-APP")
    
    # Verifica que o estado foi alterado e persistido
    saved = po_repo.get_by_id("PO-APP")
    assert saved.status == "APPROVED"

def test_approve_po_fails_if_not_found(setup_repos):
    _, po_repo = setup_repos
    uc = ApprovePurchaseOrderUseCase(po_repo)
    
    with pytest.raises(ValueError, match="não encontrado"):
        uc.execute("PO-GHOST")
