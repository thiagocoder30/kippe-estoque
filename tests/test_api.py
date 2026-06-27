import pytest
import os
from src.infrastructure.config import Config

@pytest.fixture
def client():
    # Evita importação circular, importando apenas dentro do escopo de teste
    from app import app, container
    
    # Injeta a Configuração de Teste no Container Global
    test_config = Config.for_testing()
    container.config = test_config
    
    # Reseta os Singletons para forçar a recriação com os novos caminhos (data/test_strict.db)
    container._logger = None
    container._repository = None
    container._use_case = None
    
    # Inicializa o banco de testes isolado
    container.repository._init_db()
    with container.repository._get_connection() as conn:
        conn.execute('DELETE FROM products')
        conn.execute('DELETE FROM batches')
        conn.execute('DELETE FROM transactions')
        conn.commit()
        
    app.config['TESTING'] = True
    with app.test_client() as test_client:
        yield test_client
        
    # Limpeza segura (Teardown)
    if os.path.exists(test_config.DB_PATH): os.remove(test_config.DB_PATH)
    if os.path.exists(test_config.LOG_PATH): os.remove(test_config.LOG_PATH)

def test_api_create_and_list(client):
    res_post = client.post('/api/produto', json={'id': 'SR-71', 'name': 'Pão de Forma'})
    assert res_post.status_code == 201
    client.post('/api/entrada', json={'id': 'SR-71', 'amount': 5, 'expiration_date': '2030-12-31', 'batch_code': 'LT01'})
    res_get = client.get('/api/produtos')
    assert res_get.status_code == 200
    assert res_get.json[0]['name'] == 'Pão de Forma'
    assert res_get.json[0]['quantity'] == 5

def test_api_stock_movement(client):
    client.post('/api/produto', json={'id': 'SR-72', 'name': 'Leite'})
    client.post('/api/entrada', json={'id': 'SR-72', 'amount': 10, 'expiration_date': '2030-12-31', 'batch_code': 'LT1'})
    client.post('/api/entrada', json={'id': 'SR-72', 'amount': 5, 'expiration_date': '2030-12-31', 'batch_code': 'LT2'})
    res_check = client.get('/api/produto/SR-72')
    assert res_check.json['quantity'] == 15
