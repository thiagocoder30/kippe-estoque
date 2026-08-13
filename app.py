from flask import Flask, jsonify, request, session, send_from_directory
from src.infrastructure.container import Container

container = Container()
app = Flask(__name__)
app.secret_key = container.config.SECRET_KEY

def _has_valid_session():
    if container.config.ENV == "testing" and "X-Test-Operator-Override" in request.headers: return True
    return 'operator_id' in session

@app.route('/')
def index():
    return send_from_directory('web', 'index.html')

@app.route('/web/<path:filename>', methods=['GET'])
def web_assets(filename):
    return send_from_directory('web', filename)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'system': 'KIPPE WMS',
        'gateway': 'flask'
    }), 200

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    res = container.auth_use_case.authenticate(data.get('id'), data.get('pin'))
    if res.is_success:
        session['operator_id'] = res.value.id
        session['operator_name'] = res.value.name
        session['operator_role'] = res.value.role
        return jsonify({'message': 'OK', 'operator': {'id': res.value.id, 'name': res.value.name, 'role': res.value.role}}), 200
    return jsonify({'error': res.error}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Sessão encerrada'}), 200

@app.route('/api/auth/me', methods=['GET'])
def me():
    if _has_valid_session():
        op_id = request.headers.get("X-Test-Operator-Override") if container.config.ENV == "testing" and "X-Test-Operator-Override" in request.headers else session.get('operator_id')
        return jsonify({'authenticated': True, 'operator': {'id': op_id, 'name': session.get('operator_name', 'Test Agent'), 'role': session.get('operator_role', 'OPERADOR')}})
    return jsonify({'authenticated': False}), 200


@app.route('/api/categorias', methods=['GET'])
def get_categorias():
    return jsonify([{'id': c.id, 'name': c.name, 'parent_id': c.parent_id} for c in container.category_use_case.list_all()])
@app.route('/api/categoria', methods=['POST'])
def create_categoria():
    if not _has_valid_session(): return jsonify({'error': 'Operador não autenticado.'}), 401
    data = request.json or {}
    res = container.category_use_case.create_category(data.get('id'), data.get('name'), data.get('parent_id'))
    if res.is_success: return jsonify({'message': 'OK'}), 201
    if "Autorização negada" in res.error: return jsonify({"error": res.error}), 403
    return jsonify({'error': res.error}), 400

@app.route('/api/produtos', methods=['GET'])
def get_produtos():
    return jsonify([{'id': p.id, 'name': p.name, 'quantity': p.quantity} for p in container.use_case.list_all()])

@app.route('/api/produto/<sku>', methods=['GET'])
@app.route('/api/sku/<sku>', methods=['GET'])
def get_produto(sku):
    p = container.product_repository.get_by_id(sku)
    return jsonify({'id': p.id, 'name': p.name, 'quantity': p.quantity}) if p else (jsonify({'error': 'Not found'}), 404)

@app.route('/api/reposicao/<sku>', methods=['GET'])
def get_picking_info(sku):
    res = container.use_case.get_picking_info(sku)
    return jsonify(res.value) if res.is_success else (jsonify({'error': res.error}), 404)

# ========================================================
# PROTECTED ROUTES (HTTP Auth Normalization 401)
# ========================================================
@app.route('/api/produto', methods=['POST'])
def create_produto():
    if not _has_valid_session(): return jsonify({'error': 'Operador não autenticado.'}), 401
    data = request.json or {}
    res = container.use_case.create_product(data.get('id'), data.get('name'), data.get('unit_of_measure', 'un'), data.get('status', 'ATIVO'), data.get('category_id'))
    return (jsonify({'message': 'OK'}), 201) if res.is_success else (jsonify({'error': res.error}), 400)



@app.route('/api/adjustment', methods=['POST'])
def adjustment_stock():
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    data = request.json or {}

    product_id = data.get('sku') or data.get('id')
    amount = data.get('quantity') or data.get('amount')
    reason = data.get('divergence_type') or data.get('reason') or "CONTAGEM"

    res = container.use_case.execute_adjustment(
        product_id,
        amount,
        reason,
        data.get('batch_code'),
        data.get('warehouse_id', 'WH-PADRAO')
    )

    if res.is_success:
        return jsonify({
            'message': 'Ajuste registrado.'
        }), 200

    return jsonify({
        'error': res.error
    }), 400



@app.route('/api/putaway', methods=['POST'])
def putaway_stock():
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    data = request.json or {}

    product_id = data.get('sku') or data.get('id')
    batch_code = data.get('batch_code')
    location_id = data.get('location_id') or data.get('location')

    res = container.use_case.execute_putaway(
        product_id,
        batch_code,
        location_id
    )

    if res.is_success:
        return jsonify({
            'message': 'Putaway registrado.'
        }), 200

    return jsonify({
        'error': res.error
    }), 400


@app.route('/api/receive', methods=['POST'])
def receive_stock():
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    data = request.json or {}

    product_id = data.get('sku') or data.get('id')
    amount = data.get('quantity') or data.get('amount')

    res = container.use_case.execute_add(
        product_id,
        amount,
        data.get('expiration_date', ''),
        data.get('batch_code', ''),
        data.get('manufacturing_date', ''),
        data.get('supplier', 'PADRAO')
    )

    if res.is_success:
        return jsonify({
            'message': 'Entrada registrada.'
        }), 200

    return jsonify({
        'error': res.error
    }), 400


@app.route('/api/entrada', methods=['POST'])
def add_stock():
    if not _has_valid_session(): return jsonify({'error': 'Operador não autenticado.'}), 401
    data = request.json or {}
    res = container.use_case.execute_add(data.get('id'), data.get('amount'), data.get('expiration_date', ''), data.get('batch_code', ''), data.get('manufacturing_date', ''), data.get('supplier', 'PADRAO'))
    return (jsonify({'message': 'OK'}), 200) if res.is_success else (jsonify({'error': res.error}), 400)

@app.route('/api/saida', methods=['POST'])
def remove_stock():
    if not _has_valid_session(): return jsonify({'error': 'Operador não autenticado.'}), 401
    data = request.json or {}
    res = container.use_case.execute_remove(data.get('id'), data.get('amount'))
    return (jsonify({'message': 'OK'}), 200) if res.is_success else (jsonify({'error': res.error}), 400)

@app.route('/api/historico', methods=['GET'])
def get_historico(): return jsonify(container.use_case.get_recent_history())

if __name__ == '__main__':
    is_dev = (container.config.ENV == 'development')
    app.run(host=container.config.HOST, port=container.config.PORT, debug=is_dev)
