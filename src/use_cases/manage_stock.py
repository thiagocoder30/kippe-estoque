from typing import List, Dict, Any
from src.domain.product import Product
from src.domain.result import Result
from src.interfaces.product_repository import ProductRepository

class ManageStockUseCase:
    def __init__(self, repository):
        self.repository = repository

    def create_product(self, product_id: str, name: str, initial_quantity: int) -> Result[None, str]:
        if self.repository.get_by_id(product_id):
            return Result.fail(f"Produto {product_id} já cadastrado.")
        if initial_quantity < 0:
            return Result.fail("Quantidade inicial inválida.")
            
        product = Product(id=product_id, name=name, quantity=initial_quantity)
        self.repository.save(product)
        if initial_quantity > 0:
            self.repository.log_transaction(product_id, 'ENTRADA (INICIAL)', initial_quantity)
        return Result.ok(None)

    def execute_add(self, product_id: str, amount: int) -> Result[None, str]:
        product = self.repository.get_by_id(product_id)
        if not product:
            return Result.fail(f"Produto não encontrado.")
            
        res = product.add_stock(amount)
        if res.is_success:
            self.repository.save(product)
            self.repository.log_transaction(product_id, 'ENTRADA', amount)
        return res

    def execute_remove(self, product_id: str, amount: int) -> Result[None, str]:
        product = self.repository.get_by_id(product_id)
        if not product:
            return Result.fail(f"Produto não encontrado.")
            
        res = product.remove_stock(amount)
        if res.is_success:
            self.repository.save(product)
            self.repository.log_transaction(product_id, 'SAIDA', amount)
        return res

    def list_all(self) -> List[Product]:
        return self.repository.get_all()

    def get_recent_history(self) -> List[Dict[str, Any]]:
        return self.repository.get_history()
