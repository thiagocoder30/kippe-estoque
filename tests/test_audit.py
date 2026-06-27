import pytest
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.use_cases.manage_stock import ManageStockUseCase
import os

@pytest.fixture
def repo():
    db = "test_audit.db"
    repo = SQLiteProductRepository(db)
    yield repo
    if os.path.exists(db):
        os.remove(db)

def test_audit_trail_logging(repo):
    uc = ManageStockUseCase(repo)
    uc.create_product("CX-01", "Caixa Papelão", 10) # Gera ENTRADA (INICIAL)
    uc.execute_remove("CX-01", 2) # Gera SAIDA
    
    history = uc.get_recent_history()
    
    assert len(history) == 2
    assert history[0]['type'] == 'SAIDA' # Ordem DESC
    assert history[0]['amount'] == 2
    assert history[1]['type'] == 'ENTRADA (INICIAL)'
    assert history[1]['amount'] == 10
