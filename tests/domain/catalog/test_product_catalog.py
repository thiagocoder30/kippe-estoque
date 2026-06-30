from src.domain.catalog.product import Product
from src.infrastructure.persistence.memory.product_catalog import InMemoryProductCatalog

def test_catalog_retrieves_existing_product():
    repo = InMemoryProductCatalog()
    p = repo.get_by_sku("789609890001")
    assert p is not None
    assert p.description == "Detergente Ypê 500 ml"

def test_catalog_saves_new_product():
    repo = InMemoryProductCatalog()
    new_product = Product(sku="123", description="Novo Item", brand="Marca X", category="Extra")
    repo.save(new_product)
    
    loaded = repo.get_by_sku("123")
    assert loaded is not None
    assert loaded.description == "Novo Item"
