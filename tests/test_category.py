import pytest
from src.infrastructure.config import Config
from src.infrastructure.container import Container
@pytest.fixture
def category_env():
    cfg = Config.for_testing()
    c = Container(cfg)
    c.product_repository._init_db()
    with c.product_repository._get_connection() as conn:
        conn.execute('DELETE FROM products')
        conn.execute('DELETE FROM categories')
        conn.commit()
    c.identity_provider.override_id = "MGR-01"
    c.identity_provider.override_role = "GERENTE"
    yield c
def test_create_category_hierarchy(category_env):
    uc = category_env.category_use_case
    res_root = uc.create_category("MERCEARIA", "Mercearia Geral")
    assert res_root.is_success is True
    
    res_sub = uc.create_category("GRAOS", "Grãos e Cereais", parent_id="MERCEARIA")
    assert res_sub.is_success is True
    
    cats = uc.list_all()
    assert len(cats) == 2
def test_operator_cannot_create_category(category_env):
    category_env.identity_provider.override_role = "OPERADOR"
    uc = category_env.category_use_case
    res = uc.create_category("TESTE", "Teste")
    assert res.is_success is False
    assert "Autorização negada" in res.error
