import pytest
from datetime import datetime, timedelta
from src.domain.product import Product
from src.domain.reservation import Reservation
from src.domain.services.reservation_engine import ReservationEngine
def test_reservation_creates_with_default_ttl():
    p = Product(id="SKU-TTL", name="Mouse", quantity=10)
    res = ReservationEngine.create_reservation(p, 2, "OP-01")
    
    assert res.is_success is True
    reservation = res.value
    assert reservation.status == "PENDING"
    assert reservation.expires_at != ""
    assert not reservation.is_expired()
def test_reservation_engine_purges_expired_allocations():
    p = Product(id="SKU-PURGE", name="Teclado", quantity=20, reserved_quantity=5)
    
    # Criamos uma reserva já nascida vencida (1 hora atrás)
    past = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    r1 = Reservation(id="RES-1", product_id="SKU-PURGE", amount=5, operator_id="OP-01", expires_at=past)
    
    assert r1.is_expired() is True
    
    restored = ReservationEngine.purge_expired_reservations(p, [r1])
    
    assert restored == 5
    assert r1.status == "EXPIRED"
    assert p.reserved_quantity == 0 # Devolveu para a gôndola
def test_reservation_cancellation_preserves_fefo_capacity():
    p = Product(id="SKU-CANC", name="Monitor", quantity=5, reserved_quantity=5)
    r = Reservation(id="RES-2", product_id="SKU-CANC", amount=5, operator_id="OP-01")
    
    # Produto fisicamente existe, mas disponível = 0
    assert p.available_quantity == 0
    
    ReservationEngine.cancel_reservation(p, r)
    
    assert r.status == "CANCELLED"
    assert p.available_quantity == 5
