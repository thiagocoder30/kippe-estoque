from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.procurement.order import PurchaseOrder

class PurchaseOrderRepository(ABC):
    """
    Interface de Repositório para o Agregado PurchaseOrder.
    Garante que o Domínio dite o contrato sem conhecer a tecnologia de armazenamento.
    """
    @abstractmethod
    def save(self, order: PurchaseOrder) -> None:
        pass

    @abstractmethod
    def get_by_id(self, order_id: str) -> Optional[PurchaseOrder]:
        pass

    @abstractmethod
    def get_all(self) -> List[PurchaseOrder]:
        pass
