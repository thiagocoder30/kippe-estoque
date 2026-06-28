import pytest
from src.domain.product import Product
from src.domain.batch import Batch
def test_negative_stock_blocked_by_default():
    p = Product(id="SKU-NEG-1", name="Monitor")
    p.add_stock(5, "2030-01-01", "L-1")
    
    res = p.remove_stock(10, operation_type="SALE")
    assert res.is_success is False
    assert "DESATIVADA" in res.error
def test_negative_stock_allowed_for_sales_creates_overdraft_batch():
    p = Product(id="SKU-NEG-2", name="Teclado", allow_negative_stock=True)
    p.add_stock(5, "2030-01-01", "L-2")
    
    res = p.remove_stock(15, operation_type="SALE", warehouse_id="WH-1")
    assert res.is_success is True
    assert p.quantity == -10
    
    assert "OVERDRAFT-WH-1" in p.batches
    assert p.batches["OVERDRAFT-WH-1"].quantity == -10
def test_negative_stock_blocked_for_transfers_even_if_policy_allowed():
    p = Product(id="SKU-NEG-3", name="Mouse", allow_negative_stock=True)
    p.add_stock(5, "2030-01-01", "L-3")
    
    res = p.remove_stock(10, operation_type="TRANSFER")
    assert res.is_success is False
    assert "Transferências logísticas não podem" in res.error
