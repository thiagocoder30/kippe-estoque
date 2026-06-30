import pytest
from src.domain.warehouse.topology import Warehouse, StorageLocation
from src.security.exceptions import BusinessRuleViolation

def test_create_warehouse_and_add_lean_locations():
    wh = Warehouse(id="WH-MAIN", name="Depósito Principal")
    
    # Baseado na realidade visual avaliada
    wh.add_location("CHAO-DIR", "Paletes Chão Lado Direito")
    wh.add_location("EST-B", "Estante Metálica B")
    
    assert len(wh.locations) == 2
    assert wh.get_location("CHAO-DIR").is_active is True

def test_prevent_duplicate_locations():
    wh = Warehouse(id="WH-MAIN", name="Depósito Principal")
    wh.add_location("LOC-1", "Posição Única")
    
    with pytest.raises(BusinessRuleViolation, match="já existe"):
        wh.add_location("LOC-1", "Posição Duplicada")

def test_disable_storage_location():
    wh = Warehouse(id="WH-MAIN", name="Depósito Principal")
    loc = wh.add_location("LOC-MAINT", "Posição Bloqueada")
    
    loc.disable()
    assert loc.is_active is False
    
    loc.enable()
    assert loc.is_active is True

def test_warehouse_must_have_id_and_name():
    with pytest.raises(ValueError, match="código identificador"):
        Warehouse(id="", name="Centro de Distribuição")
    
    with pytest.raises(ValueError, match="nome institucional"):
        Warehouse(id="CD-1", name="")
