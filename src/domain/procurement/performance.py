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
