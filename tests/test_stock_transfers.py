import pytest
from src.domain.product import Product
from src.domain.batch import Batch
from src.domain.services.stock_transfer_engine import StockTransferEngine
def test_stock_transfer_conserves_total_mass_across_warehouses():
    p = Product(id="SKU-MOVE", name="Arroz 5kg", quantity=100)
    b1 = Batch(code="L01", product_id="SKU-MOVE", quantity=100, expiration_date="2032-01-01", warehouse_id="CD-CONTAGEM")
    p.batches["L01"] = b1
    
    # Transfere 40 unidades de Contagem para Betim
    res = StockTransferEngine.execute_transfer(p, 40, "CD-CONTAGEM", "CD-BETIM")
    
    assert res.is_success is True
    assert p.get_stock_by_warehouse("CD-CONTAGEM") == 60
    assert p.get_stock_by_warehouse("CD-BETIM") == 40
    assert p.quantity == 100  # Invariante física de conservação de massa global
def test_stock_transfer_blocks_insufficient_origin_stock():
    p = Product(id="SKU-MOVE-2", name="Feijão", quantity=50)
    b1 = Batch(code="L02", product_id="SKU-MOVE-2", quantity=50, expiration_date="2032-01-01", warehouse_id="CD-CONTAGEM")
    p.batches["L02"] = b1
    
    res = StockTransferEngine.execute_transfer(p, 60, "CD-CONTAGEM", "CD-BETIM")
    assert res.is_success is False
    assert "Estoque insuficiente na origem" in res.error
def test_stock_transfer_prevents_same_warehouse_routing():
    p = Product(id="SKU-MOVE-3", name="Açúcar", quantity=10)
    res = StockTransferEngine.execute_transfer(p, 5, "CD-BETIM", "CD-BETIM")
    assert res.is_success is False
    assert "armazéns de origem e destino devem ser distintos" in res.error
