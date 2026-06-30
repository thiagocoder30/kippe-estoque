import json
from src.security.exceptions import ValidationException, NotFoundException, BusinessRuleViolation

class FailurePolicy:
    """
    Política Centralizada de Classificação de Falhas.
    Distingue erros transientes (recuperáveis) de falhas permanentes (irrecuperáveis).
    """
    @staticmethod
    def is_transient(exc: Exception) -> bool:
        # Erros de validação, regras de negócio e violações estruturais são permanentes
        if isinstance(exc, (ValidationException, NotFoundException, BusinessRuleViolation)):
            return False
        if isinstance(exc, json.JSONDecodeError):
            return False
            
        # Erros de sistema operacional, permissões temporárias e estouros de tempo são transientes
        if isinstance(exc, (OSError, PermissionError, TimeoutError, ConnectionError)):
            return True
            
        return False
