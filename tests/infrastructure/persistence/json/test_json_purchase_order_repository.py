import os
import json
import pytest
from src.domain.procurement.order import PurchaseOrder
from src.infrastructure.persistence.json.purchase_order_repository import JsonPurchaseOrderRepository

@pytest.fixture
def temp_json_repo(tmp_path):
    """Fornece um repositório isolado usando o diretório temporário do pytest"""
    file_path = tmp_path / "test_purchase_orders.json"
    return JsonPurchaseOrderRepository(file_path=str(file_path))

def test_json_repository_saves_and_retrieves_order(temp_json_repo):
    order = PurchaseOrder(id="PO-JSON-1", supplier_id="SUP-JSON")
    order.add_item("SKU-1", 10, 50.0)
    
    # Grava e lê do disco
    temp_json_repo.save(order)
    retrieved = temp_json_repo.get_by_id("PO-JSON-1")
    
    assert retrieved is not None
    assert retrieved.id == "PO-JSON-1"
    assert retrieved.supplier_id == "SUP-JSON"
    assert len(retrieved.items) == 1
    assert retrieved.items[0].sku == "SKU-1"
    assert retrieved.items[0].unit_price.amount == 50.0

def test_json_repository_atomic_write_creates_schema_version(temp_json_repo):
    order = PurchaseOrder(id="PO-JSON-2", supplier_id="SUP-JSON")
    temp_json_repo.save(order)
    
    # Validação estrutural do JSON gerado
    with open(temp_json_repo.file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        
    assert "PO-JSON-2" in raw_data
    assert raw_data["PO-JSON-2"]["schema_version"] == "1.0"

def test_json_repository_get_all(temp_json_repo):
    temp_json_repo.save(PurchaseOrder(id="PO-A", supplier_id="S-A"))
    temp_json_repo.save(PurchaseOrder(id="PO-B", supplier_id="S-B"))
    
    orders = temp_json_repo.get_all()
    assert len(orders) == 2
    
    ids = [o.id for o in orders]
    assert "PO-A" in ids
    assert "PO-B" in ids

def test_json_repository_returns_none_for_missing(temp_json_repo):
    assert temp_json_repo.get_by_id("PO-GHOST") is None
