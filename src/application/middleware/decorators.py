from typing import Any
from src.security.correlation import ExecutionContext
from src.application.ports.observability import AuditPort
from src.security.exceptions import AuthorizationException
from src.application.ports.security import AuthorizationPort

class UseCaseAuditDecorator:
    """Decorator Transversal: Intercepta a execução para gravar auditoria sem alterar o Use Case."""
    def __init__(self, use_case: Any, action_name: str, audit_port: AuditPort, auth_port: AuthorizationPort = None):
        self._use_case = use_case
        self._action_name = action_name
        self._audit = audit_port
        self._auth = auth_port

    def execute(self, context: ExecutionContext, *args, **kwargs) -> Any:
        # 1. Autorização (Se existir porta)
        if self._auth and not self._auth.can_execute(context, self._action_name):
            self._audit.log_operation(context, self._action_name, "N/A", "FORBIDDEN")
            raise AuthorizationException(f"Usuário {context.user_id} não autorizado para {self._action_name}.")

        # 2. Execução Pura do Use Case
        try:
            result = self._use_case.execute(context, *args, **kwargs)
            
            # Tenta extrair ID do agregado retornado para o log, ou fallback
            agg_id = getattr(result, 'id', kwargs.get('order_id', args[0] if args else "UNKNOWN"))
            self._audit.log_operation(context, self._action_name, agg_id, "SUCCESS")
            return result
        except Exception as e:
            agg_id_err = kwargs.get('order_id', args[0] if args else "UNKNOWN")
            self._audit.log_operation(context, self._action_name, agg_id_err, "FAILED", {"reason": str(e)})
            raise
