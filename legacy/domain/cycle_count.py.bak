from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
@dataclass
class CycleCountTask:
    """
    Entidade: CycleCountTask
    Representa uma ordem de serviço para inventário rotativo geográfico.
    """
    id: str
    warehouse_id: str
    operator_id: str
    location_filter: str = "GLOBAL"  # Ex: Corredor A, Setor Frios
    status: str = "OPEN"             # OPEN, IN_PROGRESS, COMPLETED, APPROVED
    counted_items: Dict[str, int] = field(default_factory=dict)  # batch_code -> quantidade_contada
    created_at: str = ""
    approved_by: Optional[str] = None
    def __post_init__(self):
        if not self.id:
            raise ValueError("ID da Tarefa de Contagem é obrigatório.")
        if not self.warehouse_id:
            raise ValueError("Armazém alvo é obrigatório.")
        if not self.operator_id:
            raise ValueError("ID do Operador responsável pela contagem é obrigatório.")
        if self.status not in ["OPEN", "IN_PROGRESS", "COMPLETED", "APPROVED"]:
            raise ValueError("Status da Tarefa de Contagem inválido.")
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
