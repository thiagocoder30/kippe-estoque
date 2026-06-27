from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from .result import Result
@dataclass
class Category:
    """
    Entidade: Category (Domínio de Inventário)
    Estrutura hierárquica para classificação mercantil, viabilizando Curva ABC e Regras Fiscais.
    """
    id: str  # Código da Categoria (Ex: BEB, LAT, LIMP)
    name: str  
    description: str = ""
    parent_id: Optional[str] = None  # Suporte a Árvore N-Depth
    active: bool = True
    sort_order: int = 0
    classification_rules: Dict[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.id or not isinstance(self.id, str) or len(self.id.strip()) == 0:
            raise ValueError("Violação de Invariante: O Código da Categoria é obrigatório.")
        if not self.name or not isinstance(self.name, str) or len(self.name.strip()) == 0:
            raise ValueError("Violação de Invariante: O Nome da Categoria não pode ser vazio.")
        if self.parent_id == self.id:
            raise ValueError("Violação de Invariante: Uma categoria não pode ser pai de si mesma.")
    def toggle_status(self) -> None:
        self.active = not self.active
