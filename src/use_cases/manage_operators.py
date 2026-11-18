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

    def list_operators(self) -> list[Operator]:
        return self.repository.list_all()

    def delete_operator(self, target_id: str, actor_id: str = "") -> Result[None, str]:
        tid = str(target_id or "").strip()
        aid = str(actor_id or "").strip()
        if not tid:
            return Result.fail("ID do operador é obrigatório.")
        if tid == aid:
            return Result.fail("Você não pode excluir o seu próprio perfil ativo.")

        target = self.repository.get_by_id(tid)
        if not target:
            return Result.fail("Operador não encontrado.")

        if target.role == "ADMIN_SISTEMA":
            admins = [op for op in self.repository.list_all() if op.role == "ADMIN_SISTEMA"]
            if len(admins) <= 1:
                return Result.fail("Não é permitido excluir o último Administrador do Sistema.")

        deleted = self.repository.delete_by_id(tid)
        if not deleted:
            return Result.fail("Não foi possível excluir o operador.")

        self._log_info(f"Governança: Operador [{tid}] ({target.name}) excluído por [{aid or 'SYSTEM'}]")
        return Result.ok(None)

    def reset_pin(self, target_id: str, new_pin: str, actor_id: str = "") -> Result[None, str]:
        tid = str(target_id or "").strip()
        aid = str(actor_id or "").strip()
        if not tid:
            return Result.fail("ID do operador é obrigatório.")

        target = self.repository.get_by_id(tid)
        if not target:
            return Result.fail("Operador não encontrado.")

        updated_res = Operator.create(
            id=target.id,
            name=target.name,
            pin=str(new_pin or "").strip(),
            role=target.role,
        )
        if not updated_res.is_success:
            return Result.fail(updated_res.error)

        self.repository.save(updated_res.value)
        self._log_info(f"Governança: PIN do Operador [{tid}] redefinido por [{aid or 'SYSTEM'}]")
        return Result.ok(None)

    def change_own_pin(self, operator_id: str, current_pin: str, new_pin: str) -> Result[None, str]:
        oid = str(operator_id or "").strip()
        cur = str(current_pin or "").strip()
        nxt = str(new_pin or "").strip()

        if not oid:
            return Result.fail("Operador não identificado.")

        operator = self.repository.get_by_id(oid)
        if not operator:
            return Result.fail("Operador não encontrado.")

        if not operator.verify_pin(cur):
            self._log_warn(f"Auth: Tentativa de troca de PIN com senha atual incorreta [{oid}]")
            return Result.fail("PIN atual incorreto.")

        if cur == nxt:
            return Result.fail("O novo PIN deve ser diferente do PIN atual.")

        updated_res = Operator.create(
            id=operator.id,
            name=operator.name,
            pin=nxt,
            role=operator.role,
        )
        if not updated_res.is_success:
            return Result.fail(updated_res.error)

        self.repository.save(updated_res.value)
        self._log_info(f"Auth: Operador [{oid}] alterou o próprio PIN com sucesso")
        return Result.ok(None)
