from typing import Protocol

class IdentityProvider(Protocol):
    """Contrato arquitetural para resolução de Identidade de Contexto."""
    def get_current_operator_id(self) -> str: ...
