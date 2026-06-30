from abc import ABC, abstractmethod
from src.security.correlation import ExecutionContext

class AuthorizationPort(ABC):
    """Porta para o Serviço de Autorização."""
    @abstractmethod
    def can_execute(self, context: ExecutionContext, action: str) -> bool:
        pass
