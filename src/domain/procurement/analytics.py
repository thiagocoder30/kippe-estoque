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
