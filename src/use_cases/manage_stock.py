from typing import List, Dict, Any, Optional
from src.domain.product import Product
from src.domain.result import Result
from src.interfaces.logger import Logger
from src.interfaces.identity import IdentityProvider

class ManageStockUseCase:
    def __init__(self, repository, logger: Optional[Logger] = None, identity_provider: Optional[IdentityProvider] = None):
        self.repository = repository
        self.logger = logger
        self.identity = identity_provider

    def _get_op(self) -> str:
        return self.identity.get_current_operator_id() if self.identity else 'SYSTEM'

    def _get_role(self) -> str:
        return self.identity.get_current_operator_role() if self.identity else 'SYSTEM'

    def _log_info(self, msg: str):
        if self.logger: self.logger.info(msg)
        
    def _log_warn(self, msg: str):
        if self.logger: self.logger.warning(msg)

    def create_product(self, product_id: str, name: str) -> Result[None, str]:
        op_id = self._get_op()
        op_role = self._get_role()
        
        # RBAC GATE: Cadastro de novos produtos requer privilégios gerenciais
        if op_role not in ["GERENTE", "SYSTEM"]:
            self._log_warn(f"RBAC Block: Operador [{op_id}] tentou cadastrar SKU [{product_id}] sem privilégios.")
            return Result.fail("Autorização negada: Apenas GERENTES podem cadastrar novos SKUs.")

        if self.repository.get_by_id(product_id):
            self._log_warn(f"Cadastro Bloqueado: SKU [{product_id}] já existe. Operador: [{op_id}]")
            return Result.fail("Produto já cadastrado.")
            
        product = Product(id=product_id, name=name, quantity=0)
        self.repository.save(product)
        self.repository.log_transaction(product_id, 'CRIACAO DE PRODUTO', 0, op_id)
        self._log_info(f"Produto Criado: SKU [{product_id}] - {name}. Operador: [{op_id}]")
        return Result.ok(None)

    def execute_add(self, product_id: str, amount: int, expiration_date: str, batch_code: str) -> Result[None, str]:
        op_id = self._get_op()
        product = self.repository.get_by_id(product_id)
        if not product: 
            self._log_warn(f"Entrada Bloqueada: SKU [{product_id}] não encontrado. Operador: [{op_id}]")
            return Result.fail("Produto não encontrado.")
            
        res = product.add_stock(amount, expiration_date, batch_code)
        if res.is_success:
            self.repository.save(product)
            self.repository.log_transaction(product_id, f'ENTRADA (Lote {batch_code})', amount, op_id)
            self._log_info(f"Entrada Registrada: SKU [{product_id}] | Lote [{batch_code}] | Qtd: {amount}. Operador: [{op_id}]")
        else:
            self._log_warn(f"Entrada Rejeitada pelo FEFO: SKU [{product_id}] - {res.error}. Operador: [{op_id}]")
            
        return res

    def execute_remove(self, product_id: str, amount: int) -> Result[None, str]:
        op_id = self._get_op()
        product = self.repository.get_by_id(product_id)
        if not product: 
            self._log_warn(f"Saída Bloqueada: SKU [{product_id}] não encontrado. Operador: [{op_id}]")
            return Result.fail("Produto não encontrado.")
            
        res = product.remove_stock(amount)
        if res.is_success:
            self.repository.save(product)
            self.repository.log_transaction(product_id, 'SAIDA (Baixa Automática FEFO)', amount, op_id)
            self._log_info(f"Saída Registrada (FEFO): SKU [{product_id}] | Qtd: {amount}. Operador: [{op_id}]")
        else:
            self._log_warn(f"Saída Rejeitada: SKU [{product_id}] - {res.error}. Operador: [{op_id}]")
            
        return res

    def list_all(self) -> List[Product]: return self.repository.get_all()
    
    def get_picking_info(self, product_id: str) -> Result[Dict[str, Any], str]:
        product = self.repository.get_by_id(product_id)
        if not product: return Result.fail("Produto sem cadastro.")
        return Result.ok({"name": product.name, "total_quantity": product.quantity, "instructions": product.get_picking_instructions()})

    def get_recent_history(self) -> List[Dict[str, Any]]: return self.repository.get_history()
