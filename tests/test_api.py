import pytest
import os
from src.infrastructure.config import Config

@pytest.fixture
def client():
    from app import app, container
    test_config = Config.for_testing()
    container.config = test_config
    
    container._logger = None
    container._product_repository = None
    container._operator_repository = None
    container._manage_stock_use_case = None
    container._manage_operators_use_case = None
    
    container.product_repository._init_db()
    
    app.config['TESTING'] = True
    with app.test_client() as test_client:
        yield test_client
        
    if os.path.exists(test_config.DB_PATH): os.remove(test_config.DB_PATH)
    if os.path.exists(test_config.LOG_PATH): os.remove(test_config.LOG_PATH)

def test_api_create_and_list(client):
    # Passa o header de segurança de teste para simular o operador logado de forma limpa
    headers = {"X-Test-Operator-Override": "SYSTEM-TEST-AGENT"}
    
    res_post = client.post('/api/produto', json={'id': 'SR-71', 'name': 'Pão de Forma'}, headers=headers)
    assert res_post.status_code == 201
    
    client.post('/api/entrada', json={'id': 'SR-71', 'amount': 5, 'expiration_date': '2030-12-31', 'batch_code': 'LT01'}, headers=headers)
    
    res_get = client.get('/api/produtos')
    assert res_get.status_code == 200
    assert res_get.json[0]['name'] == 'Pão de Forma'
    assert res_get.json[0]['quantity'] == 5

def test_api_stock_movement(client):
    headers = {"X-Test-Operator-Override": "SYSTEM-TEST-AGENT"}
    
    client.post('/api/produto', json={'id': 'SR-72', 'name': 'Leite'}, headers=headers)
    client.post('/api/entrada', json={'id': 'SR-72', 'amount': 10, 'expiration_date': '2030-12-31', 'batch_code': 'LT1'}, headers=headers)
    client.post('/api/entrada', json={'id': 'SR-72', 'amount': 5, 'expiration_date': '2030-12-31', 'batch_code': 'LT2'}, headers=headers)
    
    res_check = client.get('/api/produto/SR-72')
    assert res_check.json['quantity'] == 15
