import pytest
from app import app, repo
import os

@pytest.fixture
def client():
    app.config['TESTING'] = True
    repo.db_path = "data/test_api_flask.db"
    repo._init_db()
    
    with repo._get_connection() as conn:
        conn.execute('DELETE FROM products')
        conn.commit()
        
    with app.test_client() as client:
        yield client
        
    if os.path.exists("data/test_api_flask.db"):
        os.remove("data/test_api_flask.db")

def test_api_create_and_list(client):
    res_post = client.post('/api/produto', json={'id': 'SR-71', 'name': 'Pão de Forma', 'quantity': 5})
    assert res_post.status_code == 201
    
    res_get = client.get('/api/produtos')
    assert res_get.status_code == 200
    assert res_get.json[0]['name'] == 'Pão de Forma'
    assert res_get.json[0]['quantity'] == 5

def test_api_stock_movement(client):
    client.post('/api/produto', json={'id': 'SR-72', 'name': 'Leite', 'quantity': 10})
    
    # +5 Entrada
    client.post('/api/entrada', json={'id': 'SR-72', 'amount': 5})
    res_check = client.get('/api/produto/SR-72')
    assert res_check.json['quantity'] == 15
    
    # -2 Saída
    client.post('/api/saida', json={'id': 'SR-72', 'amount': 2})
    res_check2 = client.get('/api/produto/SR-72')
    assert res_check2.json['quantity'] == 13
    
    # -50 Saída Inválida (Rejeição Core)
    res_fail = client.post('/api/saida', json={'id': 'SR-72', 'amount': 50})
    assert res_fail.status_code == 400
    assert "Estoque insuficiente" in res_fail.json['error']
