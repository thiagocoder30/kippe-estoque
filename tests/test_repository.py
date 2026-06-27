import pytest
import os
from src.domain.product import Product
from src.interfaces.sqlite_repository import SQLiteProductRepository

@pytest.fixture
def repo():
    # Setup: Utiliza um arquivo temporário para não sujar o banco de produção
    db_path = "data/test_estoque.db"
    repository = SQLiteProductRepository(db_path=db_path)
    yield repository
    
    # Teardown: Limpeza do banco de dados de teste após execução
    if os.path.exists(db_path):
        if os.path.exists(db_path): os.remove(db_path)

def test_repository_save_and_get(repo):
    p = Product(id="KPC-300", name="Macarrão 500g", quantity=50)
    repo.save(p)
    
    p_db = repo.get_by_id("KPC-300")
    assert p_db is not None
    assert p_db.name == "Macarrão 500g"
    assert p_db.quantity == 50

def test_repository_idempotent_update(repo):
    p = Product(id="KPC-400", name="Óleo de Soja", quantity=10)
    repo.save(p)
    
    # Simula entrada de estoque
    p.quantity = 15
    repo.save(p)
    
    p_db = repo.get_by_id("KPC-400")
    assert p_db.quantity == 15

def test_repository_get_all(repo):
    repo.save(Product(id="KPC-500", name="Açúcar 1kg", quantity=20))
    repo.save(Product(id="KPC-501", name="Café 500g", quantity=30))
    
    products = repo.get_all()
    assert len(products) >= 2
    # Verifica se os IDs constam na lista de retorno
    ids = [prod.id for prod in products]
    assert "KPC-500" in ids
    assert "KPC-501" in ids
