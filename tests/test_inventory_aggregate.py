import pytest
from src.domain.product import Product
def test_aggregate_enforces_mandatory_fields():
    with pytest.raises(ValueError, match="Nome comercial"):
        Product(id="SKU-1", name="")
    with pytest.raises(ValueError, match="SKU do produto"):
        Product(id="", name="Arroz")
def test_aggregate_enforces_valid_unit_of_measure():
    with pytest.raises(ValueError, match="Unidade de medida"):
        Product(id="SKU-1", name="Arroz", unit_of_measure="garrafa")
def test_aggregate_enforces_valid_status():
    with pytest.raises(ValueError, match="Status de comercialização"):
        Product(id="SKU-1", name="Arroz", status="DELETADO")
def test_aggregate_blocks_stock_movement_if_inactive():
    p = Product(id="SKU-1", name="Arroz", status="INATIVO")
    res_add = p.add_stock(10, "2030-12-31", "L01")
    assert res_add.is_success is False
    assert "INATIVOS" in res_add.error
def test_aggregate_removal_invariant():
    p = Product(id="SKU-1", name="Arroz")
    assert p.can_be_removed() is True
    
    p.quantity = 50
    assert p.can_be_removed() is False
