import pytest
from src.domain.product import Product
from src.domain.services.replenishment_engine import ReplenishmentEngine
def test_replenishment_metrics_calculation_triggers_reorder():
    p = Product(id="SKU-REP-1", name="Cimento 50kg", quantity=100) # Saldo de 100
    
    # Demanda: 10/dia | Lead Time: 7 dias | Safety: 5 dias
    # ES = 10 * 5 = 50
    # PR = (10 * 7) + 50 = 120
    # Como 100 <= 120, exige reposicao. Sugestao: 120 + 50 - 100 = 70.
    
    metrics = ReplenishmentEngine.calculate_replenishment_metrics(
        product=p, average_daily_demand=10.0, lead_time_days=7, safety_days=5
    )
    
    assert metrics["safety_stock"] == 50
    assert metrics["reorder_point"] == 120
    assert metrics["is_replenishment_required"] is True
    assert metrics["suggested_order_quantity"] == 70
def test_replenishment_metrics_healthy_stock():
    p = Product(id="SKU-REP-2", name="Tijolo", quantity=300) 
    
    # Demanda: 10/dia | Lead Time: 7 dias | Safety: 5 dias
    # ES = 50, PR = 120. Saldo = 300 (Saudavel)
    
    metrics = ReplenishmentEngine.calculate_replenishment_metrics(
        product=p, average_daily_demand=10.0, lead_time_days=7, safety_days=5
    )
    
    assert metrics["is_replenishment_required"] is False
    assert metrics["suggested_order_quantity"] == 0
def test_replenishment_metrics_validation_error():
    p = Product(id="SKU-REP-3", name="Areia")
    with pytest.raises(ValueError, match="devem ser positivas"):
        ReplenishmentEngine.calculate_replenishment_metrics(p, -5, 7, 5)
