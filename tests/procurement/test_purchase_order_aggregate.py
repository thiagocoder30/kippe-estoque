import pytest
from src.domain.procurement.order import PurchaseOrder, PurchaseOrderLine, MonetaryValue

def test_monetary_value_object():
    v1 = MonetaryValue(10.50)
    v2 = MonetaryValue(5.25)
    
    assert v1.amount == 10.50
    assert (v1 + v2).amount == 15.75
    assert (v1 - v2).amount == 5.25
    
    with pytest.raises(ValueError, match="Valores monetários não podem ser negativos"):
        MonetaryValue(-1.0)
        
    with pytest.raises(ValueError, match="resultaria em valor negativo"):
        v2 - v1

def test_purchase_order_line_subtotal():
    line = PurchaseOrderLine(
        sku="SKU-A",
        quantity=10,
        unit_price=MonetaryValue(100.0), # Bruto = 1000
        discount=MonetaryValue(100.0),   # -100
        tax=MonetaryValue(50.0)          # +50
    )
    assert line.subtotal.amount == 950.0

def test_purchase_order_line_discount_invariant():
    with pytest.raises(ValueError, match="Desconto não pode exceder o valor bruto"):
        PurchaseOrderLine(
            sku="SKU-B",
            quantity=1,
            unit_price=MonetaryValue(50.0),
            discount=MonetaryValue(60.0) 
        )

def test_purchase_order_creation_and_derived_total():
    order = PurchaseOrder(id="PO-1001", supplier_id="SUP-001")
    assert order.status == "DRAFT"
    
    order.add_item(sku="SKU-A", quantity=10, unit_price=5.0)
    order.add_item(sku="SKU-B", quantity=2, unit_price=50.0, discount=10.0, tax=5.0)
    
    assert len(order.items) == 2
    assert order.total_value.amount == 145.0

def test_purchase_order_enforces_supplier_and_id():
    with pytest.raises(ValueError, match="ID do pedido é obrigatório"):
        PurchaseOrder(id="", supplier_id="SUP-001")
    with pytest.raises(ValueError, match="fornecedor \\(supplier_id\\) é obrigatório"):
        PurchaseOrder(id="PO-1002", supplier_id="")

def test_approval_state_machine_invariants():
    order = PurchaseOrder(id="PO-1003", supplier_id="SUP-001")
    
    with pytest.raises(ValueError, match="Não é possível aprovar um pedido sem itens"):
        order.approve()
        
    order.add_item(sku="SKU-C", quantity=100, unit_price=1.5)
    order.approve()
    assert order.status == "APPROVED"
    
    with pytest.raises(ValueError, match="Não é possível modificar itens em estado APPROVED"):
        order.add_item(sku="SKU-D", quantity=10, unit_price=2.0)

def test_cancellation_and_reopen_state_machine():
    order = PurchaseOrder(id="PO-1004", supplier_id="SUP-001")
    order.cancel()
    assert order.status == "CANCELLED"
    
    with pytest.raises(ValueError, match="Um pedido CANCELLED está selado"):
        order.reopen()

def test_cannot_cancel_received_orders():
    order = PurchaseOrder(id="PO-1005", supplier_id="SUP-001", status="PARTIALLY_RECEIVED")
    with pytest.raises(ValueError, match="recebimento físico iniciado não podem ser cancelados"):
        order.cancel()
