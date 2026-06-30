from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.procurement.supplier import Supplier

class SupplierRepository(ABC):
    """
    Interface de Repositório para a Entidade Supplier.
    Mantém o domínio agnóstico em relação ao mecanismo de I/O.
    """
    @abstractmethod
    def save(self, supplier: Supplier) -> None:
        pass

    @abstractmethod
    def get_by_id(self, supplier_id: str) -> Optional[Supplier]:
        pass

    @abstractmethod
    def get_all(self) -> List[Supplier]:
        pass
