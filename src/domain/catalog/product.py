from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Optional

@dataclass(frozen=True)
class Product:
    """
    Entidade Raiz do Bounded Context de Catálogo.
    Descreve a natureza estática do produto, agnóstica em relação ao estoque.
    """
    sku: str
    description: str
    brand: str
    category: str

class ProductCatalogRepository(ABC):
    """
    Porta de Saída (Outbound Port) para acesso ao Catálogo Central.
    Pode ser implementada em Memória, Base de Dados ou via API externa (ERP).
    """
    @abstractmethod
    def get_by_sku(self, sku: str) -> Optional[Product]:
        pass

    @abstractmethod
    def save(self, product: Product) -> None:
        pass
