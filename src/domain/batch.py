from dataclasses import dataclass
from datetime import datetime
from typing import Any
@dataclass
class Batch:
    """
    Entidade: Batch (Domínio de Inventário)
    Garante a integridade física de recipientes temporais de estoque (Lotes).
    """
    code: str  
    product_id: str
    quantity: int
    expiration_date: str  
    manufacturing_date: str = ""  
    supplier: str = "PADRAO"
    status: str = "ATIVO"  
    traceability_id: str = ""
    def __post_init__(self):
        if not self.code or not isinstance(self.code, str) or len(self.code.strip()) == 0:
            raise ValueError("Violação de Invariante: O código do lote é estritamente obrigatório.")
        if not self.product_id or len(self.product_id.strip()) == 0:
            raise ValueError("Violação de Invariante: O lote deve estar atrelado a um SKU válido.")
        if self.quantity < 0:
            raise ValueError("Violação de Invariante: A quantidade do lote não pode ser negativa.")
        
        try:
            datetime.strptime(self.expiration_date, "%Y-%m-%d")
            if self.manufacturing_date:
                datetime.strptime(self.manufacturing_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Violação de Invariante: Formato de data inválido (Use YYYY-MM-DD).")
    def is_expired(self) -> bool:
        exp = datetime.strptime(self.expiration_date, "%Y-%m-%d").date()
        return exp <= datetime.today().date()
    def __getitem__(self, item: str) -> Any:
        if item == 'qty': return self.quantity
        if item == 'exp': return self.expiration_date
        if item == 'supplier': return self.supplier
        if item == 'status': return self.status
        raise KeyError(f"Atributo legado [{item}] indisponível na Entidade Batch.")
