from typing import List, Optional
from src.domain.category import Category
from src.domain.result import Result
from src.interfaces.logger import Logger
from src.interfaces.identity import IdentityProvider
class ManageCategoriesUseCase:
    def __init__(self, repository, logger: Optional[Logger] = None, identity_provider: Optional[IdentityProvider] = None):
        self.repository = repository
        self.logger = logger
        self.identity = identity_provider
    def _get_op(self) -> str:
        return self.identity.get_current_operator_id() if self.identity else 'SYSTEM'
    def _get_role(self) -> str:
        return self.identity.get_current_operator_role() if self.identity else 'SYSTEM'
    def _log_warn(self, msg: str):
        if self.logger: self.logger.warning(msg)
        
    def _log_info(self, msg: str):
        if self.logger: self.logger.info(msg)
    def create_category(self, cat_id: str, name: str, parent_id: Optional[str] = None) -> Result[None, str]:
        op_id = self._get_op()
        if self._get_role() not in ["GERENTE", "SYSTEM"]:
            self._log_warn(f"RBAC Block: Operador [{op_id}] tentou manipular categorias.")
            return Result.fail("Autorização negada: Apenas GERENTES podem gerenciar o plano mercantil.")
        if self.repository.get_category_by_id(cat_id):
            return Result.fail("Categoria já cadastrada.")
        if parent_id and not self.repository.get_category_by_id(parent_id):
            return Result.fail("Categoria pai não encontrada.")
        try:
            category = Category(id=cat_id, name=name, parent_id=parent_id)
        except ValueError as e:
            self._log_warn(f"Validation Block: Invariante de categoria [{cat_id}] falhou - {str(e)}")
            return Result.fail(str(e))
        self.repository.save_category(category)
        self._log_info(f"Categoria Mercantil criada: [{cat_id}] {name} por [{op_id}]")
        return Result.ok(None)
    def list_all(self) -> List[Category]:
        return self.repository.get_all_categories()
