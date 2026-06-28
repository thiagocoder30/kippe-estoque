from src.domain.product import Product
from src.domain.result import Result
class NegativeStockPolicyEngine:
    @staticmethod
    def authorize_deduction(product: Product, overdraft_amount: int, operation_type: str) -> Result[bool, str]:
        # Validações estritas de exceção: só processa se a flag de overdraft estiver ativada no Agregado
        if not getattr(product, 'allow_negative_stock', False):
            return Result.fail(f"Estoque insuficiente. Política de Estoque Negativo DESATIVADA para o SKU {product.id}.")
            
        if operation_type == "TRANSFER":
            return Result.fail(f"Estoque insuficiente. Transferências logísticas não podem gerar saldo negativo (SKU {product.id}).")
            
        return Result.ok(True)
