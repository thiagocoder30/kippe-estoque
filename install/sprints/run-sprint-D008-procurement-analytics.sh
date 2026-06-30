#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D008: PROCUREMENT ANALYTICS (READ MODEL)
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
kippe::banner_program "D" "D008" "Procurement Analytics Engine"

kippe::step 1 ${TOTAL_STEPS} "Deploying Analytics Read Models & Domain Service..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/procurement/analytics.py"
from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime
from src.domain.procurement.performance import SupplierPerformance
from src.domain.procurement.three_way_match import MatchResult
from src.domain.procurement.ledger import SupplierLedger

@dataclass(frozen=True)
class ProcurementDashboard:
    """Read Model consolidado do módulo de Compras."""
    total_purchase_orders_created: int
    three_way_match_success_rate: float
    avg_approval_time_hours: float
    avg_receipt_time_hours: float
    top_suppliers: List[SupplierPerformance]
    bottom_suppliers: List[SupplierPerformance]

class ProcurementAnalyticsEngine:
    """
    Domain Service de Leitura.
    Extrai inteligência orquestrando Read Models e o Ledger Imutável.
    Nenhuma entidade de domínio é alterada.
    """
    @staticmethod
    def generate_dashboard(
        ledger: SupplierLedger,
        match_results: List[MatchResult],
        performances: List[SupplierPerformance]
    ) -> ProcurementDashboard:
        
        # 1. Compliance (Three-Way Match Rate)
        total_matches = len(match_results)
        success_matches = sum(1 for m in match_results if m.is_matched)
        match_rate = round((success_matches / total_matches * 100.0), 2) if total_matches > 0 else 0.0

        # 2. Ranking de Fornecedores (Top e Bottom)
        sorted_perf = sorted(performances, key=lambda p: p.overall_score, reverse=True)
        top_suppliers = sorted_perf[:3]
        bottom_suppliers = sorted_perf[-3:] if len(sorted_perf) >= 3 else sorted_perf

        # 3. Tempos Médios (Mineração de Eventos do Ledger)
        po_created_events = {e.aggregate_id: e.timestamp for e in ledger.get_events_by_type("PurchaseOrderCreated")}
        po_approved_events = {e.aggregate_id: e.timestamp for e in ledger.get_events_by_type("PurchaseApproved")}
        po_received_events = {e.aggregate_id: e.timestamp for e in ledger.get_events_by_type("GoodsReceived")}

        total_appr_hours, appr_count = 0.0, 0
        total_recv_hours, recv_count = 0.0, 0
        fmt = "%Y-%m-%d %H:%M:%S"

        for po_id, created_str in po_created_events.items():
            created_dt = datetime.strptime(created_str, fmt)
            
            # Tempo de Aprovação
            if po_id in po_approved_events:
                appr_dt = datetime.strptime(po_approved_events[po_id], fmt)
                hours = (appr_dt - created_dt).total_seconds() / 3600.0
                total_appr_hours += hours
                appr_count += 1
                
            # Tempo de Recebimento (Lead Time Logístico a partir da Aprovação)
            if po_id in po_received_events and po_id in po_approved_events:
                appr_dt = datetime.strptime(po_approved_events[po_id], fmt)
                recv_dt = datetime.strptime(po_received_events[po_id], fmt)
                hours = (recv_dt - appr_dt).total_seconds() / 3600.0
                total_recv_hours += hours
                recv_count += 1

        avg_appr = round(total_appr_hours / appr_count, 2) if appr_count > 0 else 0.0
        avg_recv = round(total_recv_hours / recv_count, 2) if recv_count > 0 else 0.0

        return ProcurementDashboard(
            total_purchase_orders_created=len(po_created_events),
            three_way_match_success_rate=match_rate,
            avg_approval_time_hours=avg_appr,
            avg_receipt_time_hours=avg_recv,
            top_suppliers=top_suppliers,
            bottom_suppliers=bottom_suppliers
        )
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Test Suite for Procurement Analytics..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/procurement/test_procurement_analytics.py"
import pytest
from src.domain.procurement.analytics import ProcurementAnalyticsEngine, ProcurementDashboard
from src.domain.procurement.ledger import SupplierLedger
from src.domain.procurement.three_way_match import MatchResult
from src.domain.procurement.performance import SupplierPerformance

def test_procurement_analytics_dashboard_generation():
    # 1. Configurando Mock do Ledger com Timestamps Manipulados para Teste
    ledger = SupplierLedger()
    
    # Pedido 1: Criado -> Aprovado (2h) -> Recebido (24h após aprovação)
    e1 = ledger.append_event("EV-1", "PurchaseOrderCreated", "PO-1", {})
    object.__setattr__(e1, 'timestamp', "2026-06-01 10:00:00") # Burlar Frozen para mock
    e2 = ledger.append_event("EV-2", "PurchaseApproved", "PO-1", {})
    object.__setattr__(e2, 'timestamp', "2026-06-01 12:00:00")
    e3 = ledger.append_event("EV-3", "GoodsReceived", "PO-1", {})
    object.__setattr__(e3, 'timestamp', "2026-06-02 12:00:00")
    
    # Pedido 2: Criado -> Aprovado (4h), ainda pendente de recebimento
    e4 = ledger.append_event("EV-4", "PurchaseOrderCreated", "PO-2", {})
    object.__setattr__(e4, 'timestamp', "2026-06-05 08:00:00")
    e5 = ledger.append_event("EV-5", "PurchaseApproved", "PO-2", {})
    object.__setattr__(e5, 'timestamp', "2026-06-05 12:00:00")

    # 2. Configurando Mock do Three-Way Match (75% de sucesso)
    matches = [
        MatchResult(is_matched=True),
        MatchResult(is_matched=True),
        MatchResult(is_matched=True),
        MatchResult(is_matched=False, divergences=["Price"], quantity_delta={}, price_delta={"SKU-1": 10.0})
    ]

    # 3. Configurando Mock de Fornecedores
    perfs = [
        SupplierPerformance("SUP-1", 90.0, 90.0, 90.0, 90.0, 90.0),
        SupplierPerformance("SUP-2", 80.0, 80.0, 80.0, 80.0, 80.0),
        SupplierPerformance("SUP-3", 100.0, 100.0, 100.0, 100.0, 100.0), # Top 1
        SupplierPerformance("SUP-4", 50.0, 50.0, 50.0, 50.0, 50.0)       # Bottom 1
    ]

    # 4. Geração do Dashboard
    dashboard = ProcurementAnalyticsEngine.generate_dashboard(
        ledger=ledger,
        match_results=matches,
        performances=perfs
    )

    # 5. Asserções do Motor Analítico
    assert dashboard.total_purchase_orders_created == 2
    assert dashboard.three_way_match_success_rate == 75.0
    assert dashboard.avg_approval_time_hours == 3.0 # (2h + 4h) / 2
    assert dashboard.avg_receipt_time_hours == 24.0 # Somente o PO-1 foi recebido
    
    assert dashboard.top_suppliers[0].supplier_id == "SUP-3"
    assert dashboard.bottom_suppliers[-1].supplier_id == "SUP-4"
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Regression Suite..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto de Governança
kippe::checkpoint_create "072" "1.4.0-procurement" "D008" "SUCCESS"

kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D008 (Procurement Analytics)" \
    "D009 — Invoice Settlement" \
    "8/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Procurement Analytics Engine (D008) orquestrado e implantado."
exit 0

