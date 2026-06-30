#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D007: SUPPLIER LEDGER & PERFORMANCE ENGINE
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

# 1. Carregamento do Framework
source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

# Blindagem de Infraestrutura (Fail-Fast)
for fn in kippe::init kippe::validate_script_syntax kippe::test_execute_all kippe::checkpoint_create; do
    if ! declare -F "$fn" >/dev/null; then
        echo "[FATAL] Framework function missing: $fn. O script foi interrompido."
        exit 1
    fi
done

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=3
kippe::banner_program "D" "D007" "Supplier Ledger & Performance Engine"

kippe::step 1 ${TOTAL_STEPS} "Deploying Supplier Performance Engine & Procurement Ledger Entities..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/procurement/performance.py"
from dataclasses import dataclass
from typing import List
from src.domain.procurement.order import PurchaseOrder
from src.domain.procurement.three_way_match import MatchResult

@dataclass(frozen=True)
class SupplierPerformance:
    """Read Model Imutável representando os scores de performance do Fornecedor."""
    supplier_id: str
    delivery_score: float     # Baseado em pontualidade/lead time (0.0 a 100.0)
    quality_score: float      # Baseado em conformidade física (0.0 a 100.0)
    financial_score: float    # Baseado em divergência de preços (0.0 a 100.0)
    compliance_score: float   # Baseado na taxa de sucesso do Three-Way Match (0.0 a 100.0)
    overall_score: float      # Média consolidada ponderada

class SupplierPerformanceEngine:
    """Domain Service purista (somente-leitura) para auditoria de performance."""
    @staticmethod
    def evaluate(supplier_id: str, historical_orders: List[PurchaseOrder], match_results: List[MatchResult]) -> SupplierPerformance:
        # Filtra ordens pertencentes a este fornecedor específico
        supplier_orders = [o for o in historical_orders if o.supplier_id == supplier_id]
        
        if not supplier_orders:
            return SupplierPerformance(supplier_id, 100.0, 100.0, 100.0, 100.0, 100.0)
            
        # 1. Compliance Score & Financial/Quality metrics derivadas dos Match Results
        total_matches = len(match_results)
        successful_matches = sum(1 for m in match_results if m.is_matched)
        
        compliance = (successful_matches / total_matches * 100.0) if total_matches > 0 else 100.0
        
        # Analisa desvios financeiros e físicos
        price_deviations = 0
        qty_deviations = 0
        for m in match_results:
            if m.price_delta: price_deviations += len(m.price_delta)
            if m.quantity_delta: qty_deviations += len(m.quantity_delta)
            
        financial_score = max(0.0, 100.0 - (price_deviations * 10.0))
        quality_score = max(0.0, 100.0 - (qty_deviations * 10.0))
        
        # 2. Delivery Score simulado a partir do lead time/pontualidade do histórico de ordens recebidas
        received_count = sum(1 for o in supplier_orders if o.status in ["RECEIVED", "CLOSED"])
        delivery_score = 100.0 if received_count > 0 else 90.0
        
        overall = round((delivery_score * 0.3) + (quality_score * 0.3) + (financial_score * 0.2) + (compliance * 0.2), 2)
        
        return SupplierPerformance(
            supplier_id=supplier_id,
            delivery_score=round(delivery_score, 2),
            quality_score=round(quality_score, 2),
            financial_score=round(financial_score, 2),
            compliance_score=round(compliance, 2),
            overall_score=overall
        )
KIPPE_HUNK

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/procurement/ledger.py"
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Any

@dataclass(frozen=True)
class ProcurementEvent:
    """Representação imutável de um evento atômico no ciclo de vida de compras."""
    event_id: str
    event_type: str
    aggregate_id: str
    payload: Any
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

class SupplierLedger:
    """Livro-razão imutável e append-only exclusivo do Bounded Context de Procurement."""
    def __init__(self):
        self._events: List[ProcurementEvent] = []

    def append_event(self, event_id: str, event_type: str, aggregate_id: str, payload: Any) -> ProcurementEvent:
        allowed_types = [
            "SupplierCreated", "PurchaseOrderCreated", "PurchaseApproved",
            "GoodsReceived", "InvoiceReceived", "ThreeWayMatchSucceeded",
            "ThreeWayMatchFailed", "SupplierBlocked", "SupplierReactivated"
        ]
        if event_type not in allowed_types:
            raise ValueError(f"Tipo de evento inválido para o SupplierLedger: {event_type}")
            
        event = ProcurementEvent(
            event_id=event_id,
            event_type=event_type,
            aggregate_id=aggregate_id,
            payload=payload
        )
        self._events.append(event)
        return event

    def get_events_by_aggregate(self, aggregate_id: str) -> List[ProcurementEvent]:
        return [e for e in self._events if e.aggregate_id == aggregate_id]

    def get_events_by_type(self, event_type: str) -> List[ProcurementEvent]:
        return [e for e in self._events if e.event_type == event_type]

    @property
    def all_events(self) -> List[ProcurementEvent]:
        return list(self._events)
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Test Suite for Supplier Performance and Ledger..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/procurement/test_supplier_ledger_performance.py"
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
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Regression Suite..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto de Governança
kippe::checkpoint_create "071" "1.4.0-procurement" "D007" "SUCCESS"

kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D007 (Supplier Ledger & Performance)" \
    "D008 — Procurement Analytics" \
    "7/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Supplier Ledger & Performance Engine (D007) implantados com sucesso com isolamento semântico."
exit 0

