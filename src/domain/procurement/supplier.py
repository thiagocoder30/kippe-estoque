from dataclasses import dataclass
from typing import Any
import re

@dataclass
class Supplier:
    """
    Entidade Canônica: Supplier (Fornecedor)
    Módulo D: Procurement.
    Nasce sob a nova doutrina Contract-First: Validação estrita no construtor
    sem dependência de persistência ou adaptadores legados.
    """
    id: str
    corporate_name: str
    tax_id: str  # CNPJ/Tax Number corporativo
    email: str
    status: str = "ACTIVE"
    lead_time_days: int = 0

    def __post_init__(self):
        # Validação Hierárquica Estrita
        if not self.id or not str(self.id).strip():
            raise ValueError("O ID do fornecedor é obrigatório.")
            
        if not self.corporate_name or not str(self.corporate_name).strip():
            raise ValueError("A Razão Social (corporate_name) é obrigatória.")
            
        if not self.tax_id or not str(self.tax_id).strip():
            raise ValueError("O Documento Fiscal (tax_id) é obrigatório.")
            
        if not self.email or "@" not in str(self.email):
            raise ValueError("O endereço de email fornecido é inválido.")
            
        if self.lead_time_days < 0:
            raise ValueError("O lead time logístico não pode ser negativo.")
            
        if self.status not in ["ACTIVE", "INACTIVE", "BLOCKED"]:
            raise ValueError("Status do fornecedor inválido.")
