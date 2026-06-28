import pytest
from src.domain.product import Product
from src.domain.batch import Batch
from src.domain.services.inventory_valuation_engine import InventoryValuationEngine
def test_valuation_calculates_total_value_and_average_cost():
    p = Product(id="SKU-VAL-1", name="Óleo de Soja", quantity=150)
    
    p.batches["L-JAN"] = Batch(code="L-JAN", product_id="SKU-VAL-1", quantity=100, expiration_date="2030-01-01", cost_per_unit=5.00)
    p.batches["L-FEV"] = Batch(code="L-FEV", product_id="SKU-VAL-1", quantity=50, expiration_date="2030-02-01", cost_per_unit=8.00)
    
    result = InventoryValuationEngine.calculate_valuation(p, method="FIFO")
    
    assert result.total_quantity == 150
    assert result.total_value == (100 * 5.0) + (50 * 8.0)
    assert result.average_cost == 900 / 150
    assert result.valuation_method == "FIFO"
def test_valuation_ignores_overdraft_virtual_batches():
    p = Product(id="SKU-VAL-2", name="Açúcar", quantity=0)
    
    p.batches["L-1"] = Batch(code="L-1", product_id="SKU-VAL-2", quantity=10, expiration_date="2030-01-01", cost_per_unit=3.0)
    p.batches["OVERDRAFT-WH-1"] = Batch(code="OVERDRAFT-WH-1", product_id="SKU-VAL-2", quantity=-10, expiration_date="2099-12-31")
    
    result = InventoryValuationEngine.calculate_valuation(p)
    
    assert result.total_quantity == 10
    assert result.total_value == 30.0
def test_valuation_does_not_mutate_inventory_state():
    p = Product(id="SKU-VAL-3", name="Café", quantity=20)
    p.batches["L-1"] = Batch(code="L-1", product_id="SKU-VAL-3", quantity=20, expiration_date="2030-01-01", cost_per_unit=15.0)
    
    qty_before = p.quantity
    _ = InventoryValuationEngine.calculate_valuation(p)
    
    assert p.quantity == qty_before
