from flask import Flask, jsonify, request, render_template, session
from src.infrastructure.container import Container

container = Container()
app = Flask(__name__)
app.secret_key = container.config.SECRET_KEY

def _get_active_operator_id():
    """
    Mecanismo de Resolução de Contexto de Segurança.
    Verifica a sessão real do cookie ou o cabeçalho de Override exclusivo de testes.
    """
    if container.config.ENV == "testing" and "X-Test-Operator-Override" in request.headers:
        return request.headers.get("X-Test-Operator-Override")
    return session.get('operator_id')

@app.route('/')
def index(): 
    return render_template('index.html')

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    operator_id = data.get('id')
    pin = data.get('pin')
    
    if not operator_id or not pin:
        return jsonify({'error': 'Matrícula e PIN são obrigatórios.'}), 400
        
    res = container.auth_use_case.authenticate(operator_id, pin)
    if res.is_success:
        session['operator_id'] = res.value.id
        session['operator_name'] = res.value.name
        session['operator_role'] = res.value.role
        return jsonify({
            'message': 'Autenticação bem-sucedida',
            'operator': {'id': res.value.id, 'name': res.value.name, 'role': res.value.role}
        }), 200
        
    return jsonify({'error': res.error}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Sessão encerrada com sucesso'}), 200

@app.route('/api/auth/me', methods=['GET'])
def me():
    op_id = _get_active_operator_id()
    if op_id:
        return jsonify({
            'authenticated': True,
            'operator': {'id': op_id, 'name': session.get('operator_name', 'Test Agent'), 'role': session.get('operator_role', 'OPERADOR')}
        })
    return jsonify({'authenticated': False}), 200

@app.route('/api/produtos', methods=['GET'])
def get_produtos():
    return jsonify([{
        'id': p.id, 'name': p.name, 'quantity': p.quantity
    } for p in container.use_case.list_all()])

@app.route('/api/produto/<sku>', methods=['GET'])
def get_produto(sku):
    p = container.product_repository.get_by_id(sku)
    return jsonify({'id': p.id, 'name': p.name, 'quantity': p.quantity}) if p else (jsonify({'error': 'Not found'}), 404)

@app.route('/api/reposicao/<sku>', methods=['GET'])
def get_picking_info(sku):
    res = container.use_case.get_picking_info(sku)
    return jsonify(res.value) if res.is_success else (jsonify({'error': res.error}), 404)

# ========================================================
# PROTECTED WRITE-MODEL ROUTES (EXIGEM RESOLUÇÃO DE OPERADOR)
# ========================================================
@app.route('/api/produto', methods=['POST'])
def create_produto():
    if not _get_active_operator_id():
        return jsonify({'error': 'SISTEMA BLOQUEOU: Operador não autenticado no terminal.'}), 401
    data = request.json or {}
    res = container.use_case.create_product(data.get('id'), data.get('name'))
    return (jsonify({'message': 'OK'}), 201) if res.is_success else (jsonify({'error': res.error}), 400)

@app.route('/api/entrada', methods=['POST'])
def add_stock():
    if not _get_active_operator_id():
        return jsonify({'error': 'SISTEMA BLOQUEOU: Operador não autenticado no terminal.'}), 401
    data = request.json or {}
    res = container.use_case.execute_add(data.get('id'), data.get('amount'), data.get('expiration_date', ''), data.get('batch_code', ''))
    return (jsonify({'message': 'OK'}), 200) if res.is_success else (jsonify({'error': res.error}), 400)

@app.route('/api/saida', methods=['POST'])
def remove_stock():
    if not _get_active_operator_id():
        return jsonify({'error': 'SISTEMA BLOQUEOU: Operador não autenticado no terminal.'}), 401
    data = request.json or {}
    res = container.use_case.execute_remove(data.get('id'), data.get('amount'))
    return (jsonify({'message': 'OK'}), 200) if res.is_success else (jsonify({'error': res.error}), 400)

@app.route('/api/historico', methods=['GET'])
def get_historico(): 
    return jsonify(container.use_case.get_recent_history())

if __name__ == '__main__':
    is_dev = (container.config.ENV == 'development')
    app.run(host=container.config.HOST, port=container.config.PORT, debug=is_dev)
