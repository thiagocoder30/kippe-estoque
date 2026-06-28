import pytest
from datetime import datetime, timedelta
from src.domain.product import Product
from src.domain.batch import Batch
def test_fefo_policy_blocks_expired_stock_allocation():
    p = Product(id="SKU-FEFO", name="Iogurte")
    
    ontem = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    amanha = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    p.batches["L-VENCIDO"] = Batch(code="L-VENCIDO", product_id="SKU-FEFO", quantity=10, expiration_date=ontem)
    p.batches["L-VALIDO"] = Batch(code="L-VALIDO", product_id="SKU-FEFO", quantity=5, expiration_date=amanha)
    p.quantity = 15
    
    res = p.remove_stock(10)
    
    assert res.is_success is False
    assert "Estoque insuficiente de lotes válidos" in res.error
    assert p.quantity == 15 
def test_fefo_policy_depletes_correct_batch_sequence():
    p = Product(id="SKU-FEFO-2", name="Leite")
    
    hoje_mais_10 = (datetime.today() + timedelta(days=10)).strftime("%Y-%m-%d")
    hoje_mais_20 = (datetime.today() + timedelta(days=20)).strftime("%Y-%m-%d")
    
    p.batches["L-LONGE"] = Batch(code="L-LONGE", product_id="SKU-FEFO-2", quantity=20, expiration_date=hoje_mais_20)
    p.batches["L-PERTO"] = Batch(code="L-PERTO", product_id="SKU-FEFO-2", quantity=10, expiration_date=hoje_mais_10)
    p.quantity = 30
    
    res = p.remove_stock(15)
    
    assert res.is_success is True
    assert p.batches["L-PERTO"].quantity == 0
    assert p.batches["L-LONGE"].quantity == 15
    assert p.quantity == 15
