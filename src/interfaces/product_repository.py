from typing import Protocol, List, Optional
from src.domain.product import Product

class ProductRepository(Protocol):
    """
    Interface (Protocolo) do Repositório de Produtos.
    Garante que o Core não dependa de detalhes do Banco de Dados.
    """
    def save(self, product: Product) -> None:
        ...

    def get_by_id(self, product_id: str) -> Optional[Product]:
        ...
    
    def get_all(self) -> List[Product]:
        ...
