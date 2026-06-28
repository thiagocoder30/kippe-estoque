#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A: FOUNDATION
# SPRINT A005.2 (HOTFIX ARCHITECTURE)
# SECURITY MIGRATION BRIDGE & TEST CONTEXT INJECTION
# ============================================================

set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${ROOT}"

export KIPPE_ROOT="${ROOT}"
export KIPPE_LOG_DIR="${ROOT}/reports/logs"

source install/lib/bootstrap.sh
source install/lib/testing.sh

kippe::init
kippe::init_environment

trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=4

kippe::banner_program \
    "A" \
    "A005.2" \
    "Security Migration Bridge"

kippe::step 1 ${TOTAL_STEPS} "Injecting Test Security Context into app.py..."
cat << 'EOF' > "${KIPPE_ROOT}/app.py"
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
EOF

kippe::step 2 ${TOTAL_STEPS} "Refactoring test_api.py to inject Test Security Header via Fixture..."
cat << 'EOF' > "${KIPPE_ROOT}/tests/test_api.py"
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
EOF

kippe::step 3 ${TOTAL_STEPS} "Re-running Complete Pipeline Validation (19 Passed Target)..."
kippe::test_execute_all

kippe::step 4 ${TOTAL_STEPS} "Updating Master Executive State & Committing..."
cat << 'EOF' > ESTADO_PROJETO.md
# 🌐 KIPPE PLATFORM: Institutional Retail Operations

## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 2 (Profissional).

## 2. Status Executive
* **Programa Atual:** PROGRAMA B (Identity & Security)
* **Gate Alvo:** GATE B - Security Ready
* **Última Entrega:** Sprint A005.2 (Security Migration Bridge)

## 3. Diretórios e Artefatos Essenciais
* `data/` - (Fronteira de persistência SQLite local)
* `src/infrastructure/config.py` - (12-Factor App Config)
* `app.py` - (API com Security Context Resolution Layer para ambiente de testes)
* `reports/logs/` - (Logs físicos com contrato de persistência garantido)

## 4. Próxima Ação Requerida
* **Sprint SEC003 (Nominal Audit Trail):** Com a ponte de compatibilidade reestabelecida e a suíte de testes operando 100% verde, podemos avançar para vincular nominalmente o `operator_id` gerado por esse ecossistema de sessões direto na persistência da tabela `transactions` do banco SQLite, quebrando definitivamente o anonimato operacional.
EOF

kippe::checkpoint_create \
    "011" \
    "1.0.0" \
    "A005.2" \
    "SUCCESS"

kippe::manifest_create \
    "A005.2" \
    "A" \
    "1.0.0" \
    "SUCCESS" \
    "SEC003"

git add app.py tests/test_api.py ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_A005.2.json
git commit -m "fix(security): implementa Test Security Context e reestabelece retrocompatibilidade com API legada (A005.2)" || true

kippe::banner_finish
kippe::success "Security Migration Bridge successfully built."
echo -e "\nNext Sprint: SEC003 (Nominal Audit Trail)\n"
EOF

