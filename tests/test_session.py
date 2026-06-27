import pytest
import os
from src.infrastructure.config import Config
from src.infrastructure.container import Container

@pytest.fixture
def test_env():
    from app import app, container
    cfg = Config.for_testing()
    container.config = cfg
    container._logger = None
    container._product_repository = None
    container._operator_repository = None
    container._manage_stock_use_case = None
    container._manage_operators_use_case = None
    
    container.operator_repository._init_db()
    container.product_repository._init_db()
    
    # Injeta operador de teste criptografado
    container.auth_use_case.register("2000", "Caixa Chão Loja", "4321", "OPERADOR")
    
    app.config['TESTING'] = True
    app.secret_key = cfg.SECRET_KEY
    
    with app.test_client() as client:
        yield client
        
    if os.path.exists(cfg.DB_PATH): os.remove(cfg.DB_PATH)
    if os.path.exists(cfg.LOG_PATH): os.remove(cfg.LOG_PATH)

def test_unauthenticated_requests_are_blocked(test_env):
    # Tenta criar produto sem logar
    res = test_env.post('/api/produto', json={'id': 'ERR-1', 'name': 'Falha'})
    assert res.status_code == 401
    assert "Operador não autenticado" in res.json['error']

def test_authenticated_session_flow(test_env):
    # 1. Realiza Login nominal
    res_login = test_env.post('/api/auth/login', json={'id': '2000', 'pin': '4321'})
    assert res_login.status_code == 200
    assert res_login.json['operator']['name'] == "Caixa Chão Loja"
    
    # 2. Agora a criação deve ser autorizada (201 Created)
    res_prod = test_env.post('/api/produto', json={'id': 'OK-100', 'name': 'Biscoito Recheado'})
    assert res_prod.status_code == 201
