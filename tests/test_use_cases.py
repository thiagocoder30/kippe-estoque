import pytest
import os
from src.domain.product import Product
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.use_cases.manage_stock import ManageStockUseCase

@pytest.fixture
def use_case():
    db_path = "data/test_usecase.db"
    repo = SQLiteProductRepository(db_path=db_path)
    # Limpa base para testes
    with repo._get_connection() as conn:
        conn.execute('DELETE FROM products')
        conn.commit()
        
    uc = ManageStockUseCase(repository=repo)
    yield uc
    
    if os.path.exists(db_path):
        os.remove(db_path)

def test_usecase_create_and_list(use_case):
    res = use_case.create_product("KPC-100", "Arroz 5kg", 10)
    assert res.is_success is True
    
    produtos = use_case.list_all()
    assert len(produtos) == 1
    assert produtos[0].name == "Arroz 5kg"

def test_usecase_add_stock(use_case):
    use_case.create_product("KPC-200", "Feijão", 10)
    res = use_case.execute_add("KPC-200", 5)
    
    assert res.is_success is True
    assert use_case.list_all()[0].quantity == 15

def test_usecase_remove_stock_fail(use_case):
    use_case.create_product("KPC-300", "Açúcar", 5)
    res = use_case.execute_remove("KPC-300", 10)
    
    assert res.is_success is False
    assert "Estoque insuficiente" in res.error
    assert use_case.list_all()[0].quantity == 5
