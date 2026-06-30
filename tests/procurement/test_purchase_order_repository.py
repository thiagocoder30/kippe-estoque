import pytest
from src.domain.procurement.order import PurchaseOrder
from src.infrastructure.persistence.in_memory.purchase_order_repository import InMemoryPurchaseOrderRepository

def test_in_memory_repository_saves_and_retrieves_order():
    repo = InMemoryPurchaseOrderRepository()
    order = PurchaseOrder(id="PO-REPO-001", supplier_id="SUP-CORP")
    
    # Executa Persistência
    repo.save(order)
    
    # Executa Leitura
    retrieved = repo.get_by_id("PO-REPO-001")
    
    assert retrieved is not None
    assert retrieved.id == "PO-REPO-001"
    assert retrieved.supplier_id == "SUP-CORP"
    assert retrieved.status == "DRAFT"

def test_in_memory_repository_returns_none_for_missing_order():
    repo = InMemoryPurchaseOrderRepository()
    assert repo.get_by_id("PO-GHOST-999") is None

def test_in_memory_repository_gets_all_orders():
    repo = InMemoryPurchaseOrderRepository()
    repo.save(PurchaseOrder(id="PO-A", supplier_id="SUP-A"))
    repo.save(PurchaseOrder(id="PO-B", supplier_id="SUP-B"))
    repo.save(PurchaseOrder(id="PO-C", supplier_id="SUP-C"))
    
    all_orders = repo.get_all()
    assert len(all_orders) == 3
    
    # Verifica integridade dos IDs recuperados
    ids = [o.id for o in all_orders]
    assert "PO-A" in ids
    assert "PO-B" in ids
    assert "PO-C" in ids
