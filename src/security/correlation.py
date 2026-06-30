import uuid
from dataclasses import dataclass, field
from datetime import datetime

@dataclass(frozen=True)
class ExecutionContext:
    """
    Contexto de Execução Transversal.
    Acompanha a requisição por todas as camadas, fornecendo rastreabilidade (Correlation ID),
    identidade do utilizador e timestamp da operação.
    """
    user_id: str = "system"
    correlation_id: str = field(default_factory=lambda: f"CTX-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}")
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_log_format(self) -> str:
        return f"[CTX:{self.correlation_id} | USER:{self.user_id}]"
