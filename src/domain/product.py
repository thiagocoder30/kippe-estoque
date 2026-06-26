from dataclasses import dataclass
from .result import Result

@dataclass
class Product:
    """
    Entidade Central (Core Domain). 
    Operações Idempotentes e Complexidade de Tempo O(1).
    """
    id: str
    name: str
    quantity: int

    def add_stock(self, amount: int) -> Result[None, str]:
        if amount <= 0:
            return Result.fail("Violação de Regra: A quantidade de entrada deve ser > 0.")
        self.quantity += amount
        return Result.ok(None)

    def remove_stock(self, amount: int) -> Result[None, str]:
        if amount <= 0:
            return Result.fail("Violação de Regra: A quantidade de saída deve ser > 0.")
        if self.quantity < amount:
            return Result.fail("Violação de Regra: Estoque insuficiente para a transação.")
        self.quantity -= amount
        return Result.ok(None)
