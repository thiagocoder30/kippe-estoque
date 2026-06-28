from dataclasses import dataclass, field
from datetime import datetime
@dataclass(frozen=True)
class LedgerEntry:
    """
    Entidade: LedgerEntry (Livro-Razão Imutável)
    Garante a rastreabilidade cronológica e a integridade de todas as movimentações.
    A flag 'frozen=True' impede modificações retroativas em memória.
    """
    id: str
    product_id: str
    event_type: str  # IN, OUT, RESERVE, TRANSFER, ADJUST, COUNT
    quantity_change: int
    quantity_before: int
    quantity_after: int
    warehouse_id: str
    batch_code: str
    operator_id: str
    reference_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    def __post_init__(self):
        # Validações de Invariantes de Auditoria
        if not self.id:
            raise ValueError("O ID do registro é obrigatório.")
        if not self.operator_id:
            raise ValueError("A auditoria exige a identificação do operador (operator_id).")
        if self.event_type not in ["IN", "OUT", "RESERVE", "TRANSFER", "ADJUST", "COUNT"]:
            raise ValueError(f"Tipo de evento inválido: {self.event_type}")
        
        # Conservação da Invariante Matemática
        if self.quantity_before + self.quantity_change != self.quantity_after:
            raise ValueError(f"Invariante matemática violada: {self.quantity_before} + ({self.quantity_change}) != {self.quantity_after}.")
