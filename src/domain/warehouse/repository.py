from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.warehouse.topology import Warehouse

class WarehouseRepository(ABC):
    """Porta de saída para a persistência da topologia do armazém."""
    @abstractmethod
    def save(self, warehouse: Warehouse) -> None:
        pass

    @abstractmethod
    def get_by_id(self, warehouse_id: str) -> Optional[Warehouse]:
        pass

    @abstractmethod
    def get_all(self) -> List[Warehouse]:
        pass
