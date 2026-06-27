from flask import Flask, jsonify, request, render_template
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.use_cases.manage_stock import ManageStockUseCase

app = Flask(__name__)
# Injeção de Dependência Global da API
repo = SQLiteProductRepository("estoque_producao.db")
uc = ManageStockUseCase(repository=repo)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/produtos', methods=['GET'])
def get_produtos():
    produtos = uc.list_all()
    return jsonify([{'id': p.id, 'name': p.name, 'quantity': p.quantity} for p in produtos])

@app.route('/api/produto/<sku>', methods=['GET'])
def get_produto(sku):
    # Acesso de leitura direta para alta velocidade (Read-Model O(1))
    produto = repo.get_by_id(sku)
    if produto:
        return jsonify({'id': produto.id, 'name': produto.name, 'quantity': produto.quantity})
    return jsonify({'error': 'Produto não encontrado'}), 404

@app.route('/api/produto', methods=['POST'])
def create_produto():
    data = request.json
    res = uc.create_product(data['id'], data['name'], data.get('quantity', 0))
    if res.is_success:
        return jsonify({'message': 'Produto cadastrado com sucesso'}), 201
    return jsonify({'error': res.error}), 400

@app.route('/api/entrada', methods=['POST'])
def add_stock():
    data = request.json
    res = uc.execute_add(data['id'], data['amount'])
    if res.is_success:
        return jsonify({'message': 'Entrada registrada com sucesso'}), 200
    return jsonify({'error': res.error}), 400

@app.route('/api/saida', methods=['POST'])
def remove_stock():
    data = request.json
    res = uc.execute_remove(data['id'], data['amount'])
    if res.is_success:
        return jsonify({'message': 'Saída registrada com sucesso'}), 200
    return jsonify({'error': res.error}), 400

if __name__ == '__main__':
    # Roda ouvindo em todas as interfaces. Permitindo acesso por outros PCs no mesmo WiFi
    app.run(host='0.0.0.0', port=5000, debug=False)
