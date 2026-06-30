from typing import List, Optional, Dict
from src.domain.procurement.supplier import Supplier
from src.domain.procurement.supplier_repository import SupplierRepository

class InMemorySupplierRepository(SupplierRepository):
    def __init__(self):
        self._storage: Dict[str, Supplier] = {}

    def save(self, supplier: Supplier) -> None:
        self._storage[supplier.id] = supplier

    def get_by_id(self, supplier_id: str) -> Optional[Supplier]:
        return self._storage.get(supplier_id)

    def get_all(self) -> List[Supplier]:
        return list(self._storage.values())
