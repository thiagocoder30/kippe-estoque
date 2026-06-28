from dataclasses import dataclass

@dataclass
class Warehouse:
    """
    Entidade: Warehouse (Domínio de Inventário)
    Representa uma planta física de distribuição ou filial do ecossistema de varejo.
    """
    id: str  # Código único da planta (Ex: CD-CONTAGEM, CD-BETIM)
    name: str
    address: str = ""
    is_active: bool = True

    def __post_init__(self):
        if not self.id or len(self.id.strip()) == 0:
            raise ValueError("Violação de Invariante: O código identificador do Armazém é obrigatório.")
        if not self.name or len(self.name.strip()) == 0:
            raise ValueError("Violação de Invariante: O nome institucional do Armazém não pode ser vazio.")
