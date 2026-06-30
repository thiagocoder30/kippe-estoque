import pytest
from src.domain.warehouse.topology import Warehouse
from src.infrastructure.persistence.json.warehouse_repository import JsonWarehouseRepository

def test_warehouse_repo_persistence(tmp_path):
    file_path = tmp_path / "warehouses.json"
    repo = JsonWarehouseRepository(file_path=str(file_path))
    
    wh = Warehouse(id="WH-001", name="Armazém A")
    wh.add_location("LOC-1", "Zona Direita")
    
    repo.save(wh)
    loaded = repo.get_by_id("WH-001")
    
    assert loaded is not None
    assert loaded.name == "Armazém A"
    assert len(loaded.locations) == 1
