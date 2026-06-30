import pytest
from src.domain.procurement.order import PurchaseOrder
from src.domain.procurement.three_way_match import MatchResult
from src.domain.procurement.performance import SupplierPerformanceEngine
from src.domain.procurement.ledger import SupplierLedger

def test_supplier_performance_engine_calculation():
    o1 = PurchaseOrder(id="PO-P-01", supplier_id="SUP-PERF-1", status="RECEIVED")
    
    m1 = MatchResult(is_matched=True, divergences=[], quantity_delta={}, price_delta={})
    m2 = MatchResult(is_matched=False, divergences=["Erro"], quantity_delta={"SKU-1": 2}, price_delta={"SKU-1": 50.0})
    
    perf = SupplierPerformanceEngine.evaluate(
        supplier_id="SUP-PERF-1",
        historical_orders=[o1],
        match_results=[m1, m2]
    )
    
    assert perf.supplier_id == "SUP-PERF-1"
    assert perf.compliance_score == 50.0
    assert perf.financial_score == 90.0
    assert perf.quality_score == 90.0
    assert perf.overall_score > 0.0

def test_supplier_ledger_immutable_audit_log():
    ledger = SupplierLedger()
    
    ev1 = ledger.append_event(event_id="EV-001", event_type="SupplierCreated", aggregate_id="SUP-PERF-1", payload={"name": "Test SUP"})
    ev2 = ledger.append_event(event_id="EV-002", event_type="PurchaseOrderCreated", aggregate_id="PO-P-01", payload={"total": 1500.0})
    
    assert len(ledger.all_events) == 2
    assert ledger.get_events_by_aggregate("PO-P-01")[0].event_type == "PurchaseOrderCreated"
    
    with pytest.raises(Exception):
        ev1.event_type = "HackEvent"
        
    with pytest.raises(ValueError, match="Tipo de evento inválido"):
        ledger.append_event("EV-003", "InventoryStockMutated", "PROD-1", {})
