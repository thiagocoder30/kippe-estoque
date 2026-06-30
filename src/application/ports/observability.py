from abc import ABC, abstractmethod
from typing import Dict, Any
from src.security.correlation import ExecutionContext

class AuditPort(ABC):
    """Porta (Interface) para Auditoria. O Application Layer não conhece a implementação."""
    @abstractmethod
    def log_operation(self, context: ExecutionContext, action: str, aggregate_id: str, status: str, details: Dict[str, Any] = None) -> None:
        pass

class MetricsPort(ABC):
    """Porta para coleta de métricas de negócio (ex: Prometheus, Datadog)."""
    @abstractmethod
    def increment_counter(self, metric_name: str, tags: Dict[str, str] = None) -> None:
        pass
