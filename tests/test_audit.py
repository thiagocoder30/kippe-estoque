import pytest, os
from src.infrastructure.config import Config
from src.infrastructure.container import Container

@pytest.fixture
def test_ctx():
    cfg = Config.for_testing()
    c = Container(cfg)
    c.product_repository._init_db()
    with c.product_repository._get_connection() as conn:
        conn.execute('DELETE FROM products')
        conn.execute('DELETE FROM transactions')
        conn.commit()
    yield c
    if os.path.exists(cfg.DB_PATH): os.remove(cfg.DB_PATH)

def test_audit_trail_logging_with_identity(test_ctx):
    uc = test_ctx.use_case
    test_ctx.identity_provider.override_id = "OP-007"
    test_ctx.identity_provider.override_role = "GERENTE"
    uc.create_product("CX-01", "Caixa Papelão")
    uc.execute_add("CX-01", 10, "2030-12-31", "LOTE-X") 
    
    # Simula troca de operador no contexto global
    test_ctx.identity_provider.override_id = "OP-009"
    uc.execute_remove("CX-01", 2)
    
    history = uc.get_recent_history()
    assert len(history) == 3 
    assert history[0]['amount'] == 2
    assert history[0]['operator_id'] == "OP-009"
    assert history[1]['amount'] == 10
    assert history[1]['operator_id'] == "OP-007"
