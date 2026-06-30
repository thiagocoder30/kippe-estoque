import pytest
import json
from src.domain.procurement.supplier import Supplier
from src.infrastructure.persistence.json.supplier_repository import JsonSupplierRepository
from src.infrastructure.persistence.in_memory.supplier_repository import InMemorySupplierRepository

@pytest.fixture
def temp_json_repo(tmp_path):
    file_path = tmp_path / "test_suppliers.json"
    return JsonSupplierRepository(file_path=str(file_path))

def test_json_supplier_repository_saves_and_retrieves(temp_json_repo):
    sup = Supplier(id="SUP-JSON-01", corporate_name="Tech Corp", tax_id="000", email="x@x.com", lead_time_days=7)
    
    temp_json_repo.save(sup)
    retrieved = temp_json_repo.get_by_id("SUP-JSON-01")
    
    assert retrieved is not None
    assert retrieved.id == "SUP-JSON-01"
    assert retrieved.corporate_name == "Tech Corp"
    assert retrieved.lead_time_days == 7

def test_json_supplier_repository_schema_versioning(temp_json_repo):
    sup = Supplier(id="SUP-JSON-02", corporate_name="Data Inc", tax_id="111", email="y@y.com")
    temp_json_repo.save(sup)
    
    with open(temp_json_repo.file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        
    assert "SUP-JSON-02" in raw_data
    assert raw_data["SUP-JSON-02"]["schema_version"] == "1.0"

def test_in_memory_supplier_repository():
    repo = InMemorySupplierRepository()
    repo.save(Supplier(id="S1", corporate_name="S1", tax_id="1", email="1@1.com"))
    assert repo.get_by_id("S1") is not None
    assert repo.get_by_id("GHOST") is None
    assert len(repo.get_all()) == 1
