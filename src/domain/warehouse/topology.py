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
