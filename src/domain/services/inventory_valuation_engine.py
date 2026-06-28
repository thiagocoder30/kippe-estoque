from src.domain.product import Product
from src.domain.valuation import InventoryValuationResult
class InventoryValuationEngine:
    """
    Domain Service: InventoryValuationEngine
    Camada determinística de cálculo financeiro.
    Regra de Ouro: SÓ LÊ. Proibida a mutação do estoque ou dos lotes.
    """
    @staticmethod
    def calculate_valuation(product: Product, method: str = "FIFO") -> InventoryValuationResult:
        if method not in ["FIFO", "AVERAGE"]:
            raise ValueError(f"Método de valoração não suportado: {method}")
        total_qty = 0
        total_value = 0.0
        # Seleciona apenas os lotes físicos reais (ignora lotes virtuais de OVERDRAFT)
        valid_batches = [b for b in product.batches.values() if not b.code.startswith("OVERDRAFT") and b.quantity > 0]
        for batch in valid_batches:
            total_qty += batch.quantity
            total_value += (batch.quantity * batch.cost_per_unit)
        average_cost = total_value / total_qty if total_qty > 0 else 0.0
        return InventoryValuationResult(
            product_id=product.id,
            total_quantity=total_qty,
            total_value=total_value,
            average_cost=average_cost,
            valuation_method=method
        )
