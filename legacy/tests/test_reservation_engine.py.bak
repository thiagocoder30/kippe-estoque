import pytest
from src.domain.product import Product
from src.domain.reservation import Reservation
from src.domain.services.reservation_engine import ReservationEngine
from datetime import datetime, timedelta
from src.domain.batch import Batch
def test_reservation_engine_blocks_overselling():
    p = Product(id="SKU-RES-1", name="Cadeira", quantity=10, reserved_quantity=8)
    
    # Restam apenas 2 fisicamente disponíveis
    res = ReservationEngine.create_reservation(p, 5, "OP-01")
    assert res.is_success is False
    assert "Estoque insuficiente" in res.error
    assert p.reserved_quantity == 8
def test_reservation_engine_successful_allocation():
    p = Product(id="SKU-RES-2", name="Mesa", quantity=10, reserved_quantity=0)
    
    res = ReservationEngine.create_reservation(p, 3, "OP-01")
    assert res.is_success is True
    assert p.reserved_quantity == 3
    assert p.available_quantity == 7
    
def test_reservation_cancellation_restores_availability():
    p = Product(id="SKU-RES-3", name="Estante", quantity=10, reserved_quantity=5)
    r = Reservation(id="R1", product_id="SKU-RES-3", amount=5, operator_id="OP")
    
    res = ReservationEngine.cancel_reservation(p, r)
    assert res.is_success is True
    assert r.status == "CANCELLED"
    assert p.reserved_quantity == 0
    assert p.available_quantity == 10
def test_reservation_commit_triggers_physical_removal():
    p = Product(id="SKU-RES-4", name="Sofa")
    amanha = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    p.batches["L1"] = Batch(code="L1", product_id="SKU-RES-4", quantity=10, expiration_date=amanha)
    p.quantity = 10
    
    res_alloc = ReservationEngine.create_reservation(p, 2, "OP-01")
    r = res_alloc.value
    
    res_commit = ReservationEngine.commit_reservation(p, r)
    assert res_commit.is_success is True
    assert r.status == "FULFILLED"
    
    # 2 foram removidos fisicamente, a trava foi solta.
    assert p.reserved_quantity == 0
    assert p.quantity == 8
