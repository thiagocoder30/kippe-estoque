from src.domain.product import Product
from src.domain.result import Result

class ManageStockUseCase:
    """
    Orquestrador de Regras de Negócio (Use Case).
    Garante o fluxo correto da transação, independente do Banco de Dados.
    Complexidade O(1) herdada do Domínio.
    """
    def __init__(self):
        # Preparação para injeção de dependência futura (Repositórios/Interfaces)
        pass

    def execute_add(self, product: Product, amount: int) -> Result[None, str]:
        return product.add_stock(amount)

    def execute_remove(self, product: Product, amount: int) -> Result[None, str]:
        return product.remove_stock(amount)
