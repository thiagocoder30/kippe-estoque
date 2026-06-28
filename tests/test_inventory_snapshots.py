import pytest
from src.domain.product import Product
from src.domain.batch import Batch
from src.domain.services.snapshot_engine import SnapshotEngine
def test_snapshot_capture_and_restore_integrity():
    # Prepara o estado inicial
    p1 = Product(id="SKU-SNAP-1", name="Placa Mae", quantity=10)
    p1.batches["L-1"] = Batch(code="L-1", product_id="SKU-SNAP-1", quantity=10, expiration_date="2030-12-31")
    
    p2 = Product(id="SKU-SNAP-2", name="Memoria RAM", quantity=20, reserved_quantity=5)
    p2.batches["L-2"] = Batch(code="L-2", product_id="SKU-SNAP-2", quantity=20, expiration_date="2030-12-31", warehouse_id="WH-2")
    
    state = [p1, p2]
    
    # 1. Executa Captura
    snapshot = SnapshotEngine.capture(snapshot_id="SNAP-TEST-001", products=state, operator_id="AUDITOR-99")
    
    assert snapshot.id == "SNAP-TEST-001"
    assert snapshot.created_by == "AUDITOR-99"
    assert "Placa Mae" in snapshot.payload
    assert "Memoria RAM" in snapshot.payload
    
    # 2. Executa Restauração
    restored_state = SnapshotEngine.restore(snapshot)
    
    # 3. Valida Invariantes de Reconstrução
    assert len(restored_state) == 2
    
    r_p1 = next(p for p in restored_state if p.id == "SKU-SNAP-1")
    assert r_p1.quantity == 10
    assert r_p1.batches["L-1"].expiration_date == "2030-12-31"
    
    r_p2 = next(p for p in restored_state if p.id == "SKU-SNAP-2")
    assert r_p2.reserved_quantity == 5
    assert r_p2.batches["L-2"].warehouse_id == "WH-2"
