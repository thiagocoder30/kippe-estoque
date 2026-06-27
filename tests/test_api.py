import pytest
import os
from app import app, repo

@pytest.fixture
def client():
    app.config['TESTING'] = True
    repo.db_path = "data/test_api_flask.db"
    repo._init_db()
    with repo._get_connection() as conn:
        conn.execute('DELETE FROM products')
        conn.execute('DELETE FROM batches')
        conn.execute('DELETE FROM transactions')
        conn.commit()
    with app.test_client() as client:
        yield client
    if os.path.exists("data/test_api_flask.db"):
        os.remove("data/test_api_flask.db")

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
