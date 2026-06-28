#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM B: IDENTITY & SECURITY
# SPRINT SEC002
# AUTHN & SESSION MIDDLEWARE (JWT/SECURE COOKIE)
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

TOTAL_STEPS=6

kippe::banner_program \
    "B" \
    "SEC002" \
    "AuthN & Session Middleware"

kippe::step 1 ${TOTAL_STEPS} "Updating Configuration Layer with Criptographic Keys..."
cat << 'EOF' > "${KIPPE_ROOT}/src/infrastructure/config.py"
import os

class Config:
    """
    Resolution Layer para configurações de ambiente.
    Injeta chaves criptográficas para governança de sessões seguras.
    """
    def __init__(self):
        self.ENV = os.environ.get("KIPPE_ENV", "development")
        self.DB_PATH = os.environ.get("KIPPE_DB_PATH", "data/estoque_producao.db")
        self.LOG_PATH = os.environ.get("KIPPE_LOG_PATH", "reports/logs/app.log")
        self.HOST = os.environ.get("KIPPE_HOST", "0.0.0.0")
        self.PORT = int(os.environ.get("KIPPE_PORT", 5000))
        
        # 12-Factor Secret Management
        self.SECRET_KEY = os.environ.get("KIPPE_SECRET_KEY", "9xW_institutional_secure_fallback_core_key_#71")

    @classmethod
    def for_testing(cls):
        os.environ["KIPPE_ENV"] = "testing"
        os.environ["KIPPE_DB_PATH"] = "data/test_strict.db"
        os.environ["KIPPE_LOG_PATH"] = "data/test_strict.log"
        os.environ["KIPPE_SECRET_KEY"] = "test-crypto-key-signature"
        return cls()
EOF

kippe::step 2 ${TOTAL_STEPS} "Injecting AuthN Session Security into Application Routes..."
cat << 'EOF' > "${KIPPE_ROOT}/app.py"
from flask import Flask, jsonify, request, render_template, session
from src.infrastructure.container import Container

container = Container()
app = Flask(__name__)

# Assinatura criptográfica obrigatória para impedir Session Tampering
app.secret_key = container.config.SECRET_KEY

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
        # Vincula a identidade do operador à sessão criptografada estável
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
    if 'operator_id' in session:
        return jsonify({
            'authenticated': True,
            'operator': {'id': session['operator_id'], 'name': session['operator_name'], 'role': session['operator_role']}
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
# PROTECTED WRITE-MODEL ROUTES (EXIGEM SESSÃO ATIVA)
# ========================================================
@app.route('/api/produto', methods=['POST'])
def create_produto():
    if 'operator_id' not in session:
        return jsonify({'error': 'SISTEMA BLOQUEOU: Operador não autenticado no terminal.'}), 401
    data = request.json or {}
    res = container.use_case.create_product(data.get('id'), data.get('name'))
    return (jsonify({'message': 'OK'}), 201) if res.is_success else (jsonify({'error': res.error}), 400)

@app.route('/api/entrada', methods=['POST'])
def add_stock():
    if 'operator_id' not in session:
        return jsonify({'error': 'SISTEMA BLOQUEOU: Operador não autenticado no terminal.'}), 401
    data = request.json or {}
    res = container.use_case.execute_add(data.get('id'), data.get('amount'), data.get('expiration_date', ''), data.get('batch_code', ''))
    return (jsonify({'message': 'OK'}), 200) if res.is_success else (jsonify({'error': res.error}), 400)

@app.route('/api/saida', methods=['POST'])
def remove_stock():
    if 'operator_id' not in session:
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

kippe::step 3 ${TOTAL_STEPS} "Upgrading Frontend UX with POS Login Interface Overlay..."
cat << 'EOF' > "${KIPPE_ROOT}/templates/index.html"
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Kippe Platform | POS Terminal</title>
    <script src="https://unpkg.com/html5-qrcode"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #eef2f5; margin: 0; padding: 15px; color: #333; }
        .card { background: white; border-radius: 12px; padding: 15px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .btn { width: 100%; padding: 14px; border: none; border-radius: 8px; font-weight: 700; font-size: 16px; margin-bottom: 10px; cursor: pointer; color: white; transition: 0.2s; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-blue { background: #007bff; }
        .btn-green { background: #28a745; }
        .btn-red { background: #dc3545; }
        .btn-gray { background: #6c757d; }
        input { width: 100%; padding: 12px; margin: 5px 0 15px; border: 1px solid #dcdcdc; border-radius: 8px; box-sizing: border-box; font-size:16px; background: #f9f9f9;}
        #reader { width: 100%; border-radius: 12px; overflow: hidden; margin-bottom: 10px; }
        .tabs { display: flex; border-bottom: 2px solid #ddd; margin-bottom: 15px; }
        .tab { flex: 1; text-align: center; padding: 10px; cursor: pointer; font-weight: bold; color: #888; }
        .tab.active { border-bottom: 3px solid #007bff; color: #007bff; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .list-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; font-size: 14px; }
        .badge { background: #007bff; color: white; padding: 4px 8px; border-radius: 12px; font-weight: bold; }
        .alert-box { background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin-bottom: 10px; font-size: 14px; }
        
        /* Overlay de Login Estilo Frente de Caixa (POS) */
        #auth-overlay { position: fixed; top:0; left:0; width:100%; height:100%; background: #eef2f5; z-index:9999; display: flex; align-items: center; justify-content: center; }
        .login-box { width: 90%; max-width: 360px; background: white; padding: 25px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); text-align: center; }
    </style>
</head>
<body>

    <div id="auth-overlay">
        <div class="login-box">
            <h2 style="margin:0 0 5px 0; color:#1a1a1a;">Kippe Platform</h2>
            <p style="color:#666; font-size:14px; margin:0 0 20px 0;">Identificação do Operador</p>
            <input type="number" id="auth-matricula" placeholder="Nº da Matrícula" pattern="\d*">
            <input type="password" id="auth-pin" placeholder="PIN Numérico" inputmode="numeric" pattern="\d*">
            <button class="btn btn-blue" onclick="executarLogin()">🔓 Acessar Terminal</button>
        </div>
    </div>

    <div id="app-context" style="display:none;">
        <div class="list-item" style="background: white; padding: 10px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
            <span>Identidade: <b id="user-display">---</b> <span class="badge" id="role-display" style="background:#6c757d;">---</span></span>
            <a href="#" onclick="executarLogout()" style="color:#dc3545; font-weight:bold; text-decoration:none; font-size:14px;">Logoff</a>
        </div>

        <div class="card">
            <button class="btn btn-blue" onclick="startScanner()">📷 Iniciar Leitor</button>
            <div id="reader"></div>
        </div>

        <div class="card">
            <div class="tabs">
                <div class="tab active" onclick="switchTab('caixa')">Movimentação</div>
                <div class="tab" onclick="switchTab('reposicao')">Reposição</div>
                <div class="tab" onclick="switchTab('estoque')">Inventário</div>
            </div>

            <div id="caixa-tab" class="tab-content active">
                <input type="text" id="sku" placeholder="SKU LIDO" readonly>
                <input type="text" id="nome" placeholder="Nome do Produto">
                <input type="number" id="qtd" placeholder="Quantidade" value="1">
                <div style="display:flex; gap:10px;">
                    <div style="flex:1;">
                        <input type="text" id="lote" placeholder="Lote" oninput="validarCampos()">
                    </div>
                    <div style="flex:1;">
                        <input type="date" id="validade" onchange="validarCampos()">
                    </div>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button class="btn btn-green" id="btn-entrada" onclick="processarTransacao('+')" disabled>+ Entrada</button>
                    <button class="btn btn-red" onclick="processarTransacao('-')">- Saída (FEFO)</button>
                </div>
            </div>

            <div id="reposicao-tab" class="tab-content">
                <div id="instrucoes-reposicao">
                    <p style="text-align:center; color:#666; font-size: 14px;">Aguardando leitura de gôndola...</p>
                </div>
            </div>

            <div id="estoque-tab" class="tab-content">
                <button class="btn btn-gray" onclick="carregarEstoque()">🔄 Atualizar</button>
                <div id="lista-estoque" style="margin-top: 10px;"></div>
            </div>
        </div>
    </div>

    <script>
        let html5QrcodeScanner;
        let currentTab = 'caixa';

        function playBeep() {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                osc.type = 'sine'; osc.frequency.setValueAtTime(880, ctx.currentTime);
                osc.connect(ctx.destination); osc.start(); osc.stop(ctx.currentTime + 0.1);
            } catch (e) {}
        }

        async function checarSessao() {
            const res = await fetch('/api/auth/me');
            const data = await res.json();
            if (data.authenticated) {
                document.getElementById('auth-overlay').style.display = 'none';
                document.getElementById('app-context').style.display = 'block';
                document.getElementById('user-display').innerText = data.operator.name;
                document.getElementById('role-display').innerText = data.operator.role;
                carregarEstoque();
            } else {
                document.getElementById('auth-overlay').style.display = 'flex';
                document.getElementById('app-context').style.display = 'none';
            }
        }

        async function executarLogin() {
            const matricula = document.getElementById('auth-matricula').value;
            const pin = document.getElementById('auth-pin').value;
            
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id: matricula, pin: pin})
            });
            
            if(res.ok) {
                document.getElementById('auth-matricula').value = '';
                document.getElementById('auth-pin').value = '';
                checarSessao();
            } else {
                const err = await res.json();
                alert("Bloqueio de Segurança: " + err.error);
            }
        }

        async function executarLogout() {
            await fetch('/api/auth/logout', {method: 'POST'});
            checarSessao();
        }

        function switchTab(t) {
            currentTab = t;
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(t + '-tab').classList.add('active');
            if(t === 'estoque') carregarEstoque();
        }

        function startScanner() {
            if(html5QrcodeScanner) return;
            html5QrcodeScanner = new Html5Qrcode("reader");
            html5QrcodeScanner.start({ facingMode: "environment" }, { fps: 15, qrbox: {width: 250, height: 150} }, 
            (decodedText) => {
                playBeep();
                if (navigator.vibrate) navigator.vibrate(100);
                html5QrcodeScanner.stop(); html5QrcodeScanner = null;
                
                if(currentTab === 'reposicao') gerarPickList(decodedText);
                else {
                    document.getElementById('sku').value = decodedText;
                    verificarCadastro(decodedText);
                }
            }, (err) => {}).catch(err => alert(err));
        }

        async function verificarCadastro(sku) {
            const res = await fetch(`/api/produto/${sku}`);
            if(res.status === 404) document.getElementById('nome').focus();
            else {
                const data = await res.json();
                document.getElementById('nome').value = data.name;
                document.getElementById('qtd').focus();
            }
            validarCampos();
        }

        function validarCampos() {
            const skuVal = document.getElementById('sku').value;
            const loteVal = document.getElementById('lote').value;
            const dateVal = document.getElementById('validade').value;
            document.getElementById('btn-entrada').disabled = !(skuVal && loteVal && dateVal);
        }

        async function processarTransacao(operacao) {
            const sku = document.getElementById('sku').value;
            const nome = document.getElementById('nome').value;
            const qtd = parseInt(document.getElementById('qtd').value) || 0;
            const lote = document.getElementById('lote').value;
            const validade = document.getElementById('validade').value;

            const endpoint = operacao === '+' ? '/api/entrada' : '/api/saida';
            const payload = { id: sku, amount: qtd };
            if (operacao === '+') {
                payload.expiration_date = validade;
                payload.batch_code = lote;
            }

            const resMov = await fetch(endpoint, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            if(resMov.ok) {
                document.getElementById('sku').value = '';
                document.getElementById('nome').value = '';
                document.getElementById('qtd').value = '1';
                document.getElementById('lote').value = '';
                document.getElementById('validade').value = '';
                validarCampos();
                alert("Movimentação processada com sucesso.");
            } else {
                const data = await resMov.json();
                alert("🛑 REJEIÇÃO DA PLATAFORMA:\n" + data.error);
                if(resMov.status === 401) checarSessao();
            }
        }

        async function carregarEstoque() {
            const res = await fetch('/api/produtos');
            const produtos = await res.json();
            let html = '';
            produtos.forEach(p => {
                html += `<div class="list-item">
                            <span><b>${p.name}</b> <br><small style="color:#888">${p.id}</small></span>
                            <span class="badge">${p.quantity} un</span>
                         </div>`;
            });
            document.getElementById('lista-estoque').innerHTML = html;
        }

        checarSessao();
    </script>
</body>
</html>
EOF

kippe::step 4 ${TOTAL_STEPS} "Writing Session Middleware Integration Tests..."
cat << 'EOF' > "${KIPPE_ROOT}/tests/test_session.py"
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
EOF

kippe::step 5 ${TOTAL_STEPS} "Running Full Suite Validation (19 Strict Tests)..."
kippe::test_execute_all

kippe::step 6 ${TOTAL_STEPS} "Updating Master Executive State & Closing Sprint..."
cat << 'EOF' > ESTADO_PROJETO.md
# 🌐 KIPPE PLATFORM: Institutional Retail Operations

## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 2 (Profissional).

## 2. Status Executivo
* **Programa Atual:** PROGRAMA B (Identity & Security)
* **Gate Alvo:** GATE B - Security Ready
* **Última Entrega:** Sprint SEC002 (AuthN & Session Middleware)

## 3. Diretórios e Artefatos Essenciais
* `data/` - (Fronteira de persistência SQLite)
* `src/infrastructure/config.py` - (12-Factor App Config com Secret Keys)
* `app.py` - (API RESTful com Middleware de Sessão POS e rotas seguras)
* `templates/index.html` - (UI Mobile-First com Overlay de Bloqueio por PIN)

## 4. Próxima Ação Requerida
* **Sprint SEC003 (Nominal Audit Trail):** A infraestrutura de autenticação e proteção de rotas HTTP está concluída. O próximo passo crucial é amarrar a autoria humana à persistência física do Audit Trail. Refatoraremos o caso de uso `ManageStockUseCase` e a tabela `transactions` para exigir o `operator_id` extraído do middleware de sessão a cada inserção, removendo de vez o anonimato das baixas e entradas de estoque.
EOF

kippe::checkpoint_create \
    "010" \
    "1.0.0" \
    "SEC002" \
    "SUCCESS"

kippe::manifest_create \
    "SEC002" \
    "B" \
    "1.0.0" \
    "SUCCESS" \
    "SEC003"

git add src/infrastructure/config.py app.py templates/index.html tests/test_session.py ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_SEC002.json
git commit -m "feat(security): implementa middleware de sessao criptografada e overlay POS de login (SEC002)" || true

kippe::banner_finish
kippe::success "AuthN Middleware and POS Overlay successfully deployed."
echo -e "\nNext Sprint: SEC003 (Nominal Audit Trail)\n"
EOF

