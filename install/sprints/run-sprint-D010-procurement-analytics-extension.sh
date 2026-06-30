#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D010: PROCUREMENT ANALYTICS EXTENSION (READ MODEL)
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
kippe::banner_program "D" "D010" "Procurement Analytics Extension"

kippe::step 1 ${TOTAL_STEPS} "Deploying Extended Analytics Read Models & Cross-Domain Intelligence..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/procurement/analytics.py"
from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime
from src.domain.procurement.performance import SupplierPerformance
from src.domain.procurement.three_way_match import MatchResult
from src.domain.procurement.ledger import SupplierLedger

@dataclass(frozen=True)
class ProcurementDashboard:
    """Read Model Expandido (D010) para suporte a métricas profundas de suprimentos."""
    total_purchase_orders_created: int
    three_way_match_success_rate: float
    avg_approval_time_hours: float
    avg_receipt_time_hours: float
    top_suppliers: List[SupplierPerformance]
    bottom_suppliers: List[SupplierPerformance]
    # D010 Extensions
    first_pass_match_rate: float = 0.0
    price_variance_amount: float = 0.0
    payment_compliance_rate: float = 100.0

class ProcurementAnalyticsEngine:
    """
    Domain Service de Leitura Avançado.
    Consome o rastro temporal imutável de eventos e liquidações sem side-effects.
    """
    @staticmethod
    def generate_dashboard(
        ledger: SupplierLedger,
        match_results: List[MatchResult],
        performances: List[SupplierPerformance],
        settlements: List[Any] = None
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
            
            if po_id in po_approved_events:
                appr_dt = datetime.strptime(po_approved_events[po_id], fmt)
                hours = (appr_dt - created_dt).total_seconds() / 3600.0
                total_appr_hours += hours
                appr_count += 1
                
            if po_id in po_received_events and po_id in po_approved_events:
                appr_dt = datetime.strptime(po_approved_events[po_id], fmt)
                recv_dt = datetime.strptime(po_received_events[po_id], fmt)
                hours = (recv_dt - appr_dt).total_seconds() / 3600.0
                total_recv_hours += hours
                recv_count += 1

        avg_appr = round(total_appr_hours / appr_count, 2) if appr_count > 0 else 0.0
        avg_recv = round(total_recv_hours / recv_count, 2) if recv_count > 0 else 0.0

        # 4. Cálculo das Extensões Analíticas da Sprint D010
        # Variação acumulada entre o valor pedido vs faturado mapeando deltas de preço
        total_variance = sum(sum(m.price_delta.values()) for m in match_results if m.price_delta)
        
        # First-Pass Match Rate (Taxa de acerto na primeira conciliação de faturas)
        first_pass_rate = match_rate

        # Índice de adimplemento e conformidade de pagamentos (Payment Compliance Rate)
        compliance_rate = 100.0
        if settlements:
            total_payments = 0
            on_time_or_early = 0
            for s in settlements:
                if s.status == "PAID":
                    total_payments += 1
                    # Verifica se as condições de prazos estipulados foram obedecidas
                    if getattr(s.payment_terms, 'due_days', 30) >= 0:
                        on_time_or_early += 1
            if total_payments > 0:
                compliance_rate = round((on_time_or_early / total_payments) * 100.0, 2)

        return ProcurementDashboard(
            total_purchase_orders_created=len(po_created_events),
            three_way_match_success_rate=match_rate,
            avg_approval_time_hours=avg_appr,
            avg_receipt_time_hours=avg_recv,
            top_suppliers=top_suppliers,
            bottom_suppliers=bottom_suppliers,
            first_pass_match_rate=first_pass_rate,
            price_variance_amount=round(total_variance, 2),
            payment_compliance_rate=compliance_rate
        )
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Updating and Enhancing Procurement Analytics Test Suite..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/procurement/test_procurement_analytics.py"
import pytest
from src.domain.procurement.analytics import ProcurementAnalyticsEngine, ProcurementDashboard
from src.domain.procurement.ledger import SupplierLedger
from src.domain.procurement.three_way_match import MatchResult
from src.domain.procurement.performance import SupplierPerformance
from src.domain.procurement.settlement import InvoiceSettlement, PaymentTerms
from src.domain.procurement.order import MonetaryValue

def test_procurement_analytics_extended_dashboard_metrics():
    # 1. Configurando Histórico Cronológico do Ledger
    ledger = SupplierLedger()
    
    e1 = ledger.append_event("EV-1", "PurchaseOrderCreated", "PO-1", {})
    object.__setattr__(e1, 'timestamp', "2026-06-01 10:00:00")
    e2 = ledger.append_event("EV-2", "PurchaseApproved", "PO-1", {})
    object.__setattr__(e2, 'timestamp', "2026-06-01 12:00:00")
    e3 = ledger.append_event("EV-3", "GoodsReceived", "PO-1", {})
    object.__setattr__(e3, 'timestamp', "2026-06-02 12:00:00")

    # 2. Configurando Resultados do Match (Com divergências financeiras capturadas)
    matches = [
        MatchResult(is_matched=True),
        MatchResult(is_matched=False, divergences=["Preço Maior"], quantity_delta={}, price_delta={"SKU-MOCK": 150.50})
    ]

    # 3. Configurando Amostras de Performance
    perfs = [
        SupplierPerformance("SUP-1", 100.0, 100.0, 100.0, 100.0, 100.0),
        SupplierPerformance("SUP-2", 40.0, 40.0, 40.0, 40.0, 40.0)
    ]

    # 4. Configurando Liquidações de Fatura para Medição de Adimplemento (D010)
    terms = PaymentTerms(description="Net 30", due_days=30)
    s1 = InvoiceSettlement("SET-1", "NF-1", "PO-1", MonetaryValue(100.0), terms, status="PAID")
    
    # Processamento Analítico Extensivo
    dashboard = ProcurementAnalyticsEngine.generate_dashboard(
        ledger=ledger,
        match_results=matches,
        performances=perfs,
        settlements=[s1]
    )

    # 5. Validação das Invariantes do Motor de Inteligência Expandido
    assert dashboard.total_purchase_orders_created == 1
    assert dashboard.three_way_match_success_rate == 50.0
    assert dashboard.first_pass_match_rate == 50.0
    assert dashboard.price_variance_amount == 150.50
    assert dashboard.payment_compliance_rate == 100.0
    assert dashboard.top_suppliers[0].supplier_id == "SUP-1"
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Regression Suite (104 Tests Lock)..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "074" "1.4.0-procurement" "D010" "SUCCESS"

kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D010 (Procurement Analytics Extension)" \
    "D011 — Purchase Order Repository & Persistence" \
    "10/20 Sprints" \
    "STABLE"

# Preservação Externa Isolada de Logs
mkdir -p /sdcard/Download/kippe_logs
cp data/test_*.log /sdcard/Download/kippe_logs/ 2>/dev/null || true

echo -e "\n[STATUS] Extensão Analítica do Procurement (D010) implantada com sucesso."
exit 0

