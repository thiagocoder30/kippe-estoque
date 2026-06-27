import pytest
import os
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.use_cases.manage_stock import ManageStockUseCase

@pytest.fixture
def use_case():
    db_path = "data/test_usecase.db"
    repo = SQLiteProductRepository(db_path=db_path)
    with repo._get_connection() as conn:
        conn.execute('DELETE FROM products')
        conn.execute('DELETE FROM batches')
        conn.commit()
    yield ManageStockUseCase(repository=repo)
    if os.path.exists(db_path):
        os.remove(db_path)

def test_usecase_create_and_list(use_case):
    res = use_case.create_product("KPC-100", "Arroz 5kg")
    assert res.is_success is True
    assert len(use_case.list_all()) == 1

def test_usecase_add_stock(use_case):
    use_case.create_product("KPC-200", "Feijão")
    res = use_case.execute_add("KPC-200", 5, "2030-12-31", "LOTE-Y")
    assert res.is_success is True
    assert use_case.list_all()[0].quantity == 5

def test_usecase_remove_stock_fail(use_case):
    use_case.create_product("KPC-300", "Açúcar")
    use_case.execute_add("KPC-300", 5, "2030-12-31", "LOTE-Z")
    res = use_case.execute_remove("KPC-300", 10)
    assert res.is_success is False
    assert "Estoque físico insuficiente" in res.error
