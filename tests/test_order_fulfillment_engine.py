import pytest
from src.domain.product import Product
from src.domain.batch import Batch
from src.domain.services.order_fulfillment_engine import OrderFulfillmentAllocationEngine
def test_fulfillment_allocates_complete_order_successfully():
    p1 = Product(id="SKU-OF-1", name="Caderno", quantity=50)
    p1.batches["L-1"] = Batch(code="L-1", product_id="SKU-OF-1", quantity=50, expiration_date="2030-01-01")
    
    p2 = Product(id="SKU-OF-2", name="Caneta", quantity=100)
    p2.batches["L-2"] = Batch(code="L-2", product_id="SKU-OF-2", quantity=100, expiration_date="2030-01-01")
    
    catalog = {"SKU-OF-1": p1, "SKU-OF-2": p2}
    required = {"SKU-OF-1": 10, "SKU-OF-2": 20}
    
    res = OrderFulfillmentAllocationEngine.allocate_order("ORD-001", required, catalog, "OP-99")
    
    assert res.is_success is True
    assert p1.quantity == 40
    assert p2.quantity == 80
    assert res.value["allocated_items"]["SKU-OF-1"] == 10
def test_fulfillment_aborts_entire_order_if_one_item_fails():
    p1 = Product(id="SKU-OF-3", name="Borracha", quantity=50)
    p1.batches["L-3"] = Batch(code="L-3", product_id="SKU-OF-3", quantity=50, expiration_date="2030-01-01")
    
    p2 = Product(id="SKU-OF-4", name="Lápis", quantity=5) # Saldo insuficiente para o pedido
    p2.batches["L-4"] = Batch(code="L-4", product_id="SKU-OF-4", quantity=5, expiration_date="2030-01-01")
    
    catalog = {"SKU-OF-3": p1, "SKU-OF-4": p2}
    required = {"SKU-OF-3": 10, "SKU-OF-4": 20} # Requer 20, tem 5.
    
    res = OrderFulfillmentAllocationEngine.allocate_order("ORD-002", required, catalog, "OP-99")
    
    assert res.is_success is False
    assert "Falha na alocação do SKU SKU-OF-4" in res.error
def test_fulfillment_fails_on_missing_sku_in_catalog():
    catalog = {}
    required = {"SKU-FANTASMA": 5}
    
    res = OrderFulfillmentAllocationEngine.allocate_order("ORD-003", required, catalog, "OP-99")
    
    assert res.is_success is False
    assert "não encontrado no catálogo" in res.error
