import pytest
from src.domain.procurement.order import PurchaseOrder, PurchaseOrderLine, MonetaryValue

def test_monetary_value_object():
    v1 = MonetaryValue(10.50)
    v2 = MonetaryValue(5.25)
    assert (v1 + v2).amount == 15.75
    assert (v1 - v2).amount == 5.25

def test_purchase_order_line_subtotal():
    line = PurchaseOrderLine(sku="SKU-A", quantity=10, unit_price=MonetaryValue(100.0), discount=MonetaryValue(100.0), tax=MonetaryValue(50.0))
    assert line.subtotal.amount == 950.0

def test_purchase_order_creation_and_derived_total():
    order = PurchaseOrder(id="PO-1001", supplier_id="SUP-001")
    order.add_item(sku="SKU-A", quantity=10, unit_price=5.0)
    order.add_item(sku="SKU-B", quantity=2, unit_price=50.0, discount=10.0, tax=5.0)
    assert order.total_value.amount == 145.0

def test_approval_workflow_invariants():
    order = PurchaseOrder(id="PO-WF-003", supplier_id="SUP-99")
    with pytest.raises(ValueError, match="Não é possível submeter um pedido sem itens"):
        order.submit()
    order.add_item("SKU-K", 1, 100.0)
    with pytest.raises(ValueError, match="O pedido precisa estar APPROVED"):
        order.place_order()
    with pytest.raises(ValueError, match="Impedir recebimento antes de ORDERED"):
        order.receive_item("SKU-K", 1)

def test_data_driven_receiving_workflow():
    order = PurchaseOrder(id="PO-WF-005", supplier_id="SUP-99")
    order.add_item("SKU-X", 10, 10.0)
    order.add_item("SKU-Y", 5, 20.0)
    
    order.submit()
    order.start_approval()
    order.approve()
    order.place_order()
    assert order.status == "ORDERED"
    
    # Recebimento Parcial
    order.receive_item("SKU-X", 5)
    assert order.status == "PARTIALLY_RECEIVED"
    
    # Recebimento Complementar
    order.receive_item("SKU-X", 5)
    order.receive_item("SKU-Y", 5)
    assert order.status == "RECEIVED"
    
    # Fechamento
    order.close()
    assert order.status == "CLOSED"
    
    # Excedente físico
    with pytest.raises(ValueError, match="Impedir recebimento antes de ORDERED ou após finalizado"):
        order.receive_item("SKU-X", 1)
