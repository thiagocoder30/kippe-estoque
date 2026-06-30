from abc import ABC, abstractmethod
from typing import Optional
from src.domain.warehouse.ledger import InventoryAccount

class InventoryAccountRepository(ABC):
    """Porta de saída para a persistência do Livro-Razão (Event Store)."""
    @abstractmethod
    def save(self, account: InventoryAccount) -> None:
        pass

    @abstractmethod
    def get_by_sku(self, sku: str) -> Optional[InventoryAccount]:
        pass
