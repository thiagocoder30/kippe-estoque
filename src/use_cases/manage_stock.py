from typing import List
from src.domain.product import Product
from src.domain.result import Result
from src.interfaces.product_repository import ProductRepository

class ManageStockUseCase:
    """
    Orquestrador de Regras de Negócio.
    Agora acoplado apenas à Interface (Protocolo) do Repositório (SOLID - D).
    """
    def __init__(self, repository: ProductRepository):
        self.repository = repository

    def create_product(self, product_id: str, name: str, initial_quantity: int) -> Result[None, str]:
        if self.repository.get_by_id(product_id):
            return Result.fail(f"Produto com ID {product_id} já está cadastrado.")
        
        if initial_quantity < 0:
            return Result.fail("Quantidade inicial não pode ser negativa.")
            
        product = Product(id=product_id, name=name, quantity=initial_quantity)
        self.repository.save(product)
        return Result.ok(None)

    def execute_add(self, product_id: str, amount: int) -> Result[None, str]:
        product = self.repository.get_by_id(product_id)
        if not product:
            return Result.fail(f"Produto {product_id} não encontrado.")
            
        res = product.add_stock(amount)
        if res.is_success:
            self.repository.save(product)
        return res

    def execute_remove(self, product_id: str, amount: int) -> Result[None, str]:
        product = self.repository.get_by_id(product_id)
        if not product:
            return Result.fail(f"Produto {product_id} não encontrado.")
            
        res = product.remove_stock(amount)
        if res.is_success:
            self.repository.save(product)
        return res

    def list_all(self) -> List[Product]:
        return self.repository.get_all()
