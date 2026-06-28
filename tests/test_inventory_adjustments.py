import pytest
from src.domain.product import Product
from src.domain.batch import Batch
from src.domain.services.inventory_adjustment_engine import InventoryAdjustmentEngine
def test_adjustment_positive_adds_stock_and_creates_batch():
    p = Product(id="SKU-ADJ-1", name="Biscoito")
    res = InventoryAdjustmentEngine.execute_adjustment(
        product=p, amount=10, reason="SOBRA", operator_id="OP-01", 
        warehouse_id="WH-TEST", batch_code="L-AJUSTE"
    )
    assert res.is_success is True
    assert p.quantity == 10
    assert "L-AJUSTE" in p.batches
    assert p.batches["L-AJUSTE"].quantity == 10
    assert p.batches["L-AJUSTE"].warehouse_id == "WH-TEST"
def test_adjustment_negative_removes_stock_from_specific_batch():
    p = Product(id="SKU-ADJ-2", name="Biscoito", quantity=20)
    p.batches["L-ORIG"] = Batch(code="L-ORIG", product_id="SKU-ADJ-2", quantity=20, expiration_date="2030-12-31")
    
    res = InventoryAdjustmentEngine.execute_adjustment(
        product=p, amount=-5, reason="AVARIA", operator_id="OP-02", batch_code="L-ORIG"
    )
    assert res.is_success is True
    assert p.quantity == 15
    assert p.batches["L-ORIG"].quantity == 15
def test_adjustment_fails_on_invalid_reason_or_zero_amount():
    p = Product(id="SKU-ADJ-3", name="Biscoito")
    res1 = InventoryAdjustmentEngine.execute_adjustment(p, 10, "ROUBO", "OP-03", batch_code="L1")
    assert res1.is_success is False
    assert "Motivo de ajuste invalido" in res1.error
    
    res2 = InventoryAdjustmentEngine.execute_adjustment(p, 0, "CONTAGEM", "OP-03", batch_code="L1")
    assert res2.is_success is False
    assert "nao pode ser zero" in res2.error
def test_adjustment_negative_fails_if_insufficient_stock():
    p = Product(id="SKU-ADJ-4", name="Biscoito", quantity=5)
    p.batches["L-ORIG"] = Batch(code="L-ORIG", product_id="SKU-ADJ-4", quantity=5, expiration_date="2030-12-31")
    
    res = InventoryAdjustmentEngine.execute_adjustment(
        product=p, amount=-10, reason="PERDA", operator_id="OP-04", batch_code="L-ORIG"
    )
    assert res.is_success is False
    assert "Estoque insuficiente" in res.error
