from dataclasses import dataclass, field
from typing import List, Optional
from src.security.exceptions import BusinessRuleViolation

@dataclass
class StorageLocation:
    id: str
    name: str
    is_active: bool = True

    def disable(self): self.is_active = False
    def enable(self): self.is_active = True

@dataclass
class Warehouse:
    """
    Agregado Raiz com validação de invariantes no nascimento.
    Impede que o sistema entre em estado inválido por ID ou Nome ausente.
    """
    id: str
    name: str
    locations: List[StorageLocation] = field(default_factory=list)

    def __post_init__(self):
        if not self.id or not self.id.strip():
            raise ValueError("Warehouse deve possuir um código identificador.")
        if not self.name or not self.name.strip():
            raise ValueError("Warehouse deve possuir um nome institucional.")

    def add_location(self, location_id: str, name: str) -> StorageLocation:
        if any(loc.id == location_id for loc in self.locations):
            raise BusinessRuleViolation(f"Posição {location_id} já existe no armazém {self.id}.")

        loc = StorageLocation(id=location_id, name=name)
        self.locations.append(loc)
        return loc

    def get_location(self, location_id: str) -> Optional[StorageLocation]:
        for loc in self.locations:
            if loc.id == location_id:
                return loc
        return None

# =========================================================
# NOVA INTELIGÊNCIA: MAPEAMENTO ESTÁTICO DE CHÃO DE FÁBRICA
# =========================================================

@dataclass(frozen=True)
class PhysicalAddress:
    zone: str
    details: str

class TopologyResolver:
    """
    Mapeia regras físicas estáticas baseadas na categoria ou descrição do produto.
    Ideal para operações rápidas, evitando a sobrecarga de sistemas dinâmicos.
    """
    @staticmethod
    def get_physical_address(category: str, description: str) -> PhysicalAddress:
        cat = category.upper() if category else ""
        desc = description.upper() if description else ""
        
        # Regra 1: Limpeza (Fixo na lateral direita, no chão)
        if "LIMPEZA" in cat or "DETERGENTE" in desc or "SABÃO" in desc or "SABAO" in desc:
            return PhysicalAddress(
                zone="LATERAL DIREITA", 
                details="Paletes no chão (lateral direita ao entrar no depósito)"
            )
            
        # Regra 2: Papéis Higiênicos (Últimos boxes)
        elif "PAPEL" in cat or "PAPEIS" in cat or "HIGIÊNICO" in desc or "HIGIENICO" in desc:
            return PhysicalAddress(
                zone="BOX P E Q", 
                details="Alocação de fundo (Últimos boxes do depósito)"
            )
            
        # Regra 3: Perfumaria e Higiene Pessoal (Paletes no chão)
        elif "PERFUMARIA" in cat or "HIGIENE" in cat or "SABONETE" in desc:
            return PhysicalAddress(
                zone="PALETES NO CHÃO", 
                details="Alocação em paletes no chão (Seção de Higiene/Perfumaria)"
            )
            
        # Regra Padrão: Box Genérico (A ao O)
        return PhysicalAddress(
            zone="ÁREA DE BOXES (A ao O)", 
            details="Verificar endereçamento padrão (Níveis A1 Superior / A2 Inferior)"
        )

