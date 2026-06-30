from typing import Optional, Dict
from src.domain.catalog.product import Product, ProductCatalogRepository

class InMemoryProductCatalog(ProductCatalogRepository):
    """Adaptador de Teste/Desenvolvimento para o Catálogo de Produtos."""
    def __init__(self):
        self._db: Dict[str, Product] = {
            "789609890001": Product(
                sku="789609890001",
                description="Detergente Ypê 500 ml",
                brand="Ypê",
                category="Limpeza"
            ),
            "000000000000": Product(
                sku="000000000000",
                description="Produto Genérico Não Registado",
                brand="Genérica",
                category="Diversos"
            )
        }

    def get_by_sku(self, sku: str) -> Optional[Product]:
        return self._db.get(sku)

    def save(self, product: Product) -> None:
        self._db[product.sku] = product
