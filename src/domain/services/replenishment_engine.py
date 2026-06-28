from typing import Dict, Any
from src.domain.product import Product
class ReplenishmentEngine:
    # Domain Service: ReplenishmentEngine
    # Motor responsavel por calculos dinamicos de Ponto de Reposicao (PR)
    # e Estoque de Seguranca (ES) baseando-se em dados operacionais.
    @staticmethod
    def calculate_replenishment_metrics(product: Product, average_daily_demand: float, lead_time_days: int, safety_days: int) -> Dict[str, Any]:
        if average_daily_demand < 0 or lead_time_days < 0 or safety_days < 0:
            raise ValueError("As metricas de demanda, lead time e dias de seguranca devem ser positivas.")
        safety_stock = int(average_daily_demand * safety_days)
        reorder_point = int((average_daily_demand * lead_time_days) + safety_stock)
        
        # Consolida a quantidade fisica global disponivel deduzindo as reservas
        available_stock = product.available_quantity
        
        is_replenishment_required = available_stock <= reorder_point
        suggested_order_qty = 0
        
        if is_replenishment_required:
            # Uma heuristica basica corporativa: pedir o suficiente para cobrir PR + ES, 
            # garantindo que o saldo final apos o recebimento estabilize acima da ruptura.
            target_stock = reorder_point + safety_stock
            suggested_order_qty = max(0, target_stock - available_stock)
        return {
            "sku": product.id,
            "available_stock": available_stock,
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
            "is_replenishment_required": is_replenishment_required,
            "suggested_order_quantity": suggested_order_qty
        }
