from typing import Optional
from src.domain.operator import Operator
from src.domain.result import Result
from src.interfaces.logger import Logger

class ManageOperatorsUseCase:
    def __init__(self, repository, logger: Optional[Logger] = None):
        self.repository = repository
        self.logger = logger

    def _log_info(self, msg: str):
        if self.logger: self.logger.info(msg)
        
    def _log_warn(self, msg: str):
        if self.logger: self.logger.warning(msg)

    def register(self, id: str, name: str, pin: str, role: str = "OPERADOR") -> Result[None, str]:
        if self.repository.get_by_id(id):
            self._log_warn(f"Segurança: Tentativa de sobrescrita de cadastro do Operador [{id}]")
            return Result.fail("Operador já cadastrado no sistema.")
        
        res = Operator.create(id=id, name=name, pin=pin, role=role)
        if res.is_success:
            self.repository.save(res.value)
            self._log_info(f"Governança: Novo Operador registrado [{id}] - {name} ({role})")
            return Result.ok(None)
        
        return Result.fail(res.error)

    def authenticate(self, id: str, pin: str) -> Result[Operator, str]:
        operator = self.repository.get_by_id(id)
        if not operator:
            self._log_warn(f"Auth: Falha de login (Operador não encontrado) [{id}]")
            return Result.fail("Credenciais inválidas.")
        
        if operator.verify_pin(pin):
            self._log_info(f"Auth: Operador autenticado com sucesso [{id}]")
            return Result.ok(operator)
        
        self._log_warn(f"Auth: Falha de login (PIN incorreto) para o Operador [{id}]")
        return Result.fail("Credenciais inválidas.")
