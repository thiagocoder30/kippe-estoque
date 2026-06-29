import pytest
from src.domain.procurement.order import PurchaseOrder, PurchaseOrderLine, MonetaryValue

def test_purchase_order_full_approval_workflow():
    order = PurchaseOrder(id="PO-WF-001", supplier_id="SUP-99")
    
    # Adicionar itens (Permitido em DRAFT)
    order.add_item(sku="SKU-X", quantity=10, unit_price=10.0)
    
    # DRAFT -> SUBMITTED
    order.submit()
    assert order.status == "SUBMITTED"
    
    # SUBMITTED -> UNDER_APPROVAL
    order.start_approval()
    assert order.status == "UNDER_APPROVAL"
    
    # UNDER_APPROVAL -> APPROVED
    order.approve()
    assert order.status == "APPROVED"
    
    # Tentativa de editar itens após aprovação deve falhar
    with pytest.raises(ValueError, match="Não é possível modificar itens em estado APPROVED"):
        order.add_item(sku="SKU-Y", quantity=5, unit_price=10.0)
        
    # APPROVED -> ORDERED
    order.place_order()
    assert order.status == "ORDERED"
    
    # ORDERED -> RECEIVED
    order.receive_completely()
    assert order.status == "RECEIVED"
    
    # NUNCA voltar de RECEIVED para ORDERED
    assert not hasattr(order, "reopen")

def test_purchase_order_rejection_workflow():
    order = PurchaseOrder(id="PO-WF-002", supplier_id="SUP-99")
    order.add_item("SKU-Z", 1, 10.0)
    
    order.submit()
    order.start_approval()
    
    # UNDER_APPROVAL -> REJECTED
    order.reject()
    assert order.status == "REJECTED"
    
    # REJECTED -> DRAFT
    order.send_to_draft()
    assert order.status == "DRAFT"
    
    # Em DRAFT pode voltar a editar
    order.add_item("SKU-W", 2, 5.0)
    assert len(order.items) == 2

def test_approval_workflow_invariants():
    order = PurchaseOrder(id="PO-WF-003", supplier_id="SUP-99")
    
    # Impedir aprovação (submissão) sem linhas
    with pytest.raises(ValueError, match="Não é possível submeter um pedido sem itens"):
        order.submit()
        
    order.add_item("SKU-K", 1, 100.0)
    
    # Impedir ORDERED antes de APPROVED
    with pytest.raises(ValueError, match="O pedido precisa estar APPROVED"):
        order.place_order()
        
    # Impedir RECEIVED antes de ORDERED
    with pytest.raises(ValueError, match="Impedir RECEIVED antes de ORDERED"):
        order.receive_completely()

def test_cannot_cancel_after_receipt_starts():
    order = PurchaseOrder(id="PO-WF-004", supplier_id="SUP-99")
    order.add_item("SKU-A", 1, 10.0)
    order.submit()
    order.start_approval()
    order.approve()
    order.place_order()
    order.receive_partially()
    
    with pytest.raises(ValueError, match="recebimento físico iniciado não podem ser cancelados"):
        order.cancel()
