import pytest
import os
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.use_cases.manage_stock import ManageStockUseCase

@pytest.fixture
def repo():
    db = "data/test_audit.db"
    r = SQLiteProductRepository(db)
    yield r
    if os.path.exists(db):
        os.remove(db)

def test_audit_trail_logging(repo):
    uc = ManageStockUseCase(repo)
    uc.create_product("CX-01", "Caixa Papelão")
    uc.execute_add("CX-01", 10, "2030-12-31", "LOTE-X") # Gera Log de Entrada
    uc.execute_remove("CX-01", 2) # Gera Log de Saida
    
    history = uc.get_recent_history()
    
    assert len(history) == 2
    assert 'SAIDA' in history[0]['type'] 
    assert history[0]['amount'] == 2
    assert 'ENTRADA' in history[1]['type']
    assert history[1]['amount'] == 10
