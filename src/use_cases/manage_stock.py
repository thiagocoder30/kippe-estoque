from typing import List, Dict, Any
from src.domain.product import Product
from src.domain.result import Result

class ManageStockUseCase:
    def __init__(self, repository):
        self.repository = repository

    def create_product(self, product_id: str, name: str) -> Result[None, str]:
        if self.repository.get_by_id(product_id):
            return Result.fail("Produto já cadastrado.")
        product = Product(id=product_id, name=name, quantity=0)
        self.repository.save(product)
        return Result.ok(None)

    def execute_add(self, product_id: str, amount: int, expiration_date: str, batch_code: str) -> Result[None, str]:
        product = self.repository.get_by_id(product_id)
        if not product: return Result.fail("Produto não encontrado.")
            
        res = product.add_stock(amount, expiration_date, batch_code)
        if res.is_success:
            self.repository.save(product)
            self.repository.log_transaction(product_id, f'ENTRADA (Lote {batch_code})', amount)
        return res

    def execute_remove(self, product_id: str, amount: int) -> Result[None, str]:
        product = self.repository.get_by_id(product_id)
        if not product: return Result.fail("Produto não encontrado.")
            
        res = product.remove_stock(amount)
        if res.is_success:
            self.repository.save(product)
            self.repository.log_transaction(product_id, 'SAIDA (Baixa Automática FEFO)', amount)
        return res

    def list_all(self) -> List[Product]: return self.repository.get_all()
    
    def get_picking_info(self, product_id: str) -> Result[Dict[str, Any], str]:
        product = self.repository.get_by_id(product_id)
        if not product: return Result.fail("Produto sem cadastro.")
        
        info = {
            "name": product.name,
            "total_quantity": product.quantity,
            "instructions": product.get_picking_instructions()
        }
        return Result.ok(info)

    def get_recent_history(self) -> List[Dict[str, Any]]: return self.repository.get_history()
