import pytest
from src.domain.warehouse.movement import MovementEngine, DualStockView
from src.security.exceptions import BusinessRuleViolation

def test_movement_engine_registers_fast_event():
    event = MovementEngine.register(
        sku="DETERGENTE-X",
        quantity=6,
        movement_type="TO_STORE",
        origin="REPOSITOR_APP",
        destination="STORE"
    )
    
    assert event.sku == "DETERGENTE-X"
    assert event.quantity == 6
    assert event.movement_type == "TO_STORE"

def test_dual_stock_view_calculates_partitions():
    # Base inicial: 100 no depósito
    events = [
        MovementEngine.register("DETERGENTE-X", 10, "TO_STORE", "APP", "STORE"),
        MovementEngine.register("DETERGENTE-X", 2, "TO_STORE", "APP", "STORE"),
        MovementEngine.register("DETERGENTE-X", 3, "CONSUMPTION", "PDV", "CLIENT")
    ]
    
    view = DualStockView.calculate(events, sku="DETERGENTE-X", base_depot_stock=100)
    
    # 100 - 10 - 2 = 88 no depósito
    assert view["depot"] == 88
    # 10 + 2 - 3 consumidos = 9 na loja
    assert view["store"] == 9
    # Total = 88 + 9 = 97
    assert view["total"] == 97

def test_movement_engine_prevents_zero_quantity():
    with pytest.raises(BusinessRuleViolation, match="estritamente positiva"):
        MovementEngine.register("SKU-1", 0, "TO_STORE", "APP", "STORE")
