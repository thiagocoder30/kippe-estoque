from typing import List, Dict
from src.domain.product import Product
class WarehouseAnalytics:
    """
    Domain Service: WarehouseAnalytics
    Fornece métricas analíticas consolidadas sobre a distribuição de estoque e classificação volumétrica.
    """
    @staticmethod
    def calculate_warehouse_utilization(products: List[Product]) -> Dict[str, int]:
        """Agrupa matematicamente o volume físico total de SKUs por planta operacional."""
        utilization = {}
        for p in products:
            for batch in p.batches.values():
                wh = batch.warehouse_id
                utilization[wh] = utilization.get(wh, 0) + batch.quantity
        return utilization
    @staticmethod
    def generate_abc_distribution(products: List[Product]) -> Dict[str, str]:
        """
        Classifica os SKUs em faixas de giro físico (Curva ABC) com base no saldo acumulado.
        A: Top 20% das variações físicas de maior volume.
        B: Próximos 30% em densidade física.
        C: Restantes 50% de cauda longa de giro.
        """
        if not products:
            return {}
            
        # Consolida e ordena do maior para o menor saldo físico
        product_volumes = [(p.id, p.quantity) for p in products]
        product_volumes.sort(key=lambda x: x[1], reverse=True)
        
        total_items = len(product_volumes)
        classification = {}
        
        for index, (pid, _) in enumerate(product_volumes):
            rank = (index + 1) / total_items
            if rank <= 0.20:
                classification[pid] = "A"
            elif rank <= 0.50:
                classification[pid] = "B"
            else:
                classification[pid] = "C"
                
        return classification
