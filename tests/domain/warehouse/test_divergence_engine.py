from src.domain.warehouse.divergence import DivergenceEngine, TrustScoreEngine, InventoryRealityEngine, DivergenceEvent

def test_divergence_engine_detects_unregistered_withdrawal():
    # Sistema diz 100, Físico diz 92
    event = DivergenceEngine.evaluate(sku="DETERGENTE", system_quantity=100, physical_quantity=92)
    
    assert event is not None
    assert event.delta == -8
    assert event.divergence_type == "UNREGISTERED_WITHDRAWAL"

def test_divergence_engine_detects_expiration_loss():
    event = DivergenceEngine.evaluate(sku="IOGURTE", system_quantity=50, physical_quantity=40, reason="Produto vencido descartado")
    assert event.divergence_type == "EXPIRED_LOSS"

def test_divergence_engine_ignores_perfect_match():
    event = DivergenceEngine.evaluate(sku="CAFE", system_quantity=20, physical_quantity=20)
    assert event is None

def test_trust_score_penalization_math():
    # Simula 4 retiradas não registradas totalizando 20 unidades de erro
    events = [
        DivergenceEvent("SKU-1", 100, 95, -5, "UNREGISTERED_WITHDRAWAL", None, "2026-06-01T10:00:00"),
        DivergenceEvent("SKU-1", 95, 90, -5, "UNREGISTERED_WITHDRAWAL", None, "2026-06-05T10:00:00"),
        DivergenceEvent("SKU-1", 90, 85, -5, "UNREGISTERED_WITHDRAWAL", None, "2026-06-10T10:00:00"),
        DivergenceEvent("SKU-1", 85, 80, -5, "UNREGISTERED_WITHDRAWAL", None, "2026-06-15T10:00:00")
    ]
    
    trust = TrustScoreEngine.calculate(events)
    
    assert trust.divergence_count == 4
    assert trust.total_adjustment_volume == 20
    # Score Base (1.0) - Freq (4*0.05 = 0.20) - Volume (20*0.01 = 0.20) = 0.60
    assert trust.score == 0.60
    assert trust.risk_level == "MEDIUM"

def test_inventory_reality_snapshot_building():
    snapshot = InventoryRealityEngine.build_snapshot(sku="CAFE", system_qty=50, physical_qty=48, trust_score=0.85)
    assert snapshot.divergence == -2
    assert snapshot.trust_score == 0.85
