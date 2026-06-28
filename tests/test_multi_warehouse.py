import pytest
from src.domain.product import Product
from src.domain.batch import Batch

def test_product_aggregates_stock_per_warehouse_correctly():
    p = Product(id="SKU-MULTI", name="Oleo de Motor")
    
    # Injeta lotes distribuídos em diferentes centros de distribuição (Planta Contagem e Planta Betim)
    b1 = Batch(code="L-01", product_id="SKU-MULTI", quantity=150, expiration_date="2030-01-01", warehouse_id="CD-CONTAGEM")
    b2 = Batch(code="L-02", product_id="SKU-MULTI", quantity=50, expiration_date="2030-01-01", warehouse_id="CD-BETIM")
    
    p.batches["L-01"] = b1
    p.batches["L-02"] = b2
    p.quantity = 200
    
    # Valida o isolamento matemático dos saldos por planta
    assert p.get_stock_by_warehouse("CD-CONTAGEM") == 150
    assert p.get_stock_by_warehouse("CD-BETIM") == 50
    assert p.get_stock_by_warehouse("CD-VOLANTE") == 0

def test_warehouse_entity_invariants():
    from src.domain.warehouse import Warehouse
    with pytest.raises(ValueError, match="código identificador"):
        Warehouse(id="", name="Centro de Distribuição")
    with pytest.raises(ValueError, match="nome institucional"):
        Warehouse(id="CD-1", name="")
