from src.security.exceptions import DomainException

class CircuitBreakerOpenException(DomainException):
    """Lançada quando o disjuntor está aberto e rejeita execuções preventivamente."""
    pass
