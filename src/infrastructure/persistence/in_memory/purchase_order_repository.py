from typing import List, Optional, Dict
from src.domain.procurement.order import PurchaseOrder
from src.domain.procurement.repository import PurchaseOrderRepository

class InMemoryPurchaseOrderRepository(PurchaseOrderRepository):
    """
    Implementação volátil para testes e isolamento de estado.
    Localizada na camada de Infrastructure, obedecendo ao Dependency Inversion Principle.
    """
    def __init__(self):
        self._storage: Dict[str, PurchaseOrder] = {}

    def save(self, order: PurchaseOrder) -> None:
        self._storage[order.id] = order

    def get_by_id(self, order_id: str) -> Optional[PurchaseOrder]:
        return self._storage.get(order_id)

    def get_all(self) -> List[PurchaseOrder]:
        return list(self._storage.values())
