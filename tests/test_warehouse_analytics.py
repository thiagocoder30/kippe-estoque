import pytest
from src.domain.product import Product
from src.domain.batch import Batch
from src.domain.services.warehouse_analytics import WarehouseAnalytics
def test_warehouse_utilization_aggregation():
    p1 = Product(id="P1", name="Item A", quantity=50)
    p1.batches["B1"] = Batch(code="B1", product_id="P1", quantity=50, expiration_date="2030-01-01", warehouse_id="WH-CONTAGEM")
    
    p2 = Product(id="P2", name="Item B", quantity=100)
    p2.batches["B2"] = Batch(code="B2", product_id="P2", quantity=70, expiration_date="2030-01-01", warehouse_id="WH-CONTAGEM")
    p2.batches["B3"] = Batch(code="B3", product_id="P2", quantity=30, expiration_date="2030-01-01", warehouse_id="WH-BETIM")
    
    utilization = WarehouseAnalytics.calculate_warehouse_utilization([p1, p2])
    
    assert utilization["WH-CONTAGEM"] == 120
    assert utilization["WH-BETIM"] == 30
def test_abc_distribution_classification():
    products = [
        Product(id="SKU-A", name="Líder de Giro", quantity=500),
        Product(id="SKU-B1", name="Intermediário 1", quantity=200),
        Product(id="SKU-B2", name="Intermediário 2", quantity=150),
        Product(id="SKU-C1", name="Baixo Giro 1", quantity=50),
        Product(id="SKU-C2", name="Baixo Giro 2", quantity=10)
    ]
    
    abc = WarehouseAnalytics.generate_abc_distribution(products)
    
    assert abc["SKU-A"] == "A"
    assert abc["SKU-B1"] == "B"
    assert abc["SKU-C2"] == "C"
