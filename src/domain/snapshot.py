from dataclasses import dataclass, field
from datetime import datetime
@dataclass(frozen=True)
class InventorySnapshot:
    """
    Entidade: InventorySnapshot
    Captura imutável do estado consolidado do inventário em um instante T.
    """
    id: str
    payload: str  # Representação JSON estrita do estado (Aggregate Roots + Batches)
    created_by: str = "SYSTEM"
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    def __post_init__(self):
        if not self.id:
            raise ValueError("O identificador do Snapshot é obrigatório.")
        if not self.payload:
            raise ValueError("O payload do Snapshot não pode ser vazio.")
