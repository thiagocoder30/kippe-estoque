from dataclasses import dataclass, field
from typing import Dict
@dataclass
class OutboundOrder:
    """
    Entidade: OutboundOrder
    Representa a ordem de saída física da mercadoria no armazém.
    Estados: ALLOCATED -> PICKING -> DISPATCHED
    """
    id: str
    warehouse_id: str
    operator_id: str
    allocated_items: Dict[str, int]
    status: str = "ALLOCATED"
    tracking_code: str = ""
    def __post_init__(self):
        if not self.id or not self.warehouse_id:
            raise ValueError("ID da Ordem e Armazém são obrigatórios.")
        if not self.allocated_items:
            raise ValueError("A ordem deve conter itens alocados.")
        if self.status not in ["ALLOCATED", "PICKING", "DISPATCHED"]:
            raise ValueError("Status de expedição inválido.")
