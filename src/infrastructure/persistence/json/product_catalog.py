import os
import json
from typing import Optional, Dict
from src.domain.catalog.product import Product, ProductCatalogRepository

class JsonProductCatalog(ProductCatalogRepository):
    """Adaptador de Persistência Institucional para o Catálogo."""
    def __init__(self, file_path: str = "data/catalog/products.json"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            self._write_all({})

    def _read_all(self) -> Dict[str, dict]:
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_all(self, data: Dict[str, dict]) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_by_sku(self, sku: str) -> Optional[Product]:
        data = self._read_all()
        if sku not in data:
            return None
        p = data[sku]
        return Product(
            sku=p["sku"], description=p["description"],
            brand=p["brand"], category=p["category"]
        )

    def save(self, product: Product) -> None:
        data = self._read_all()
        data[product.sku] = {
            "sku": product.sku,
            "description": product.description,
            "brand": product.brand,
            "category": product.category
        }
        self._write_all(data)
