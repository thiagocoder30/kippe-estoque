#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A: FOUNDATION
# SPRINT A005
# DEPENDENCY INJECTION CONTAINER (IoC)
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
    "A" \
    "A005" \
    "Dependency Injection Container"

kippe::step 1 ${TOTAL_STEPS} "Building IoC Container (Pure Python)..."
cat << 'EOF' > "${KIPPE_ROOT}/src/infrastructure/container.py"
from src.infrastructure.config import Config
from src.infrastructure.logger_adapter import FileLogger
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.use_cases.manage_stock import ManageStockUseCase

class Container:
    """
    IoC Container Institucional.
    Gerencia o ciclo de vida e resolve dependências em cascata com Lazy Loading.
    """
    def __init__(self, config_override: Config = None):
        self.config = config_override or Config()
        self._logger = None
        self._repository = None
        self._use_case = None

    @property
    def logger(self) -> FileLogger:
        if not self._logger:
            self._logger = FileLogger(self.config.LOG_PATH)
        return self._logger

    @property
    def repository(self) -> SQLiteProductRepository:
        if not self._repository:
            self._repository = SQLiteProductRepository(self.config.DB_PATH)
        return self._repository

    @property
    def use_case(self) -> ManageStockUseCase:
        if not self._use_case:
            self._use_case = ManageStockUseCase(
                repository=self.repository,
                logger=self.logger
            )
        return self._use_case
EOF

kippe::step 2 ${TOTAL_STEPS} "Refactoring app.py to Delegate to IoC Container..."
cat << 'EOF' > "${KIPPE_ROOT}/app.py"
from flask import Flask, jsonify, request, render_template
from src.infrastructure.container import Container

# O Container assume o Bootstrapping da Plataforma
container = Container()
app = Flask(__name__)

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/produtos', methods=['GET'])
def get_produtos():
    return jsonify([{
        'id': p.id, 'name': p.name, 'quantity': p.quantity
    } for p in container.use_case.list_all()])

@app.route('/api/produto/<sku>', methods=['GET'])
def get_produto(sku):
    p = container.repository.get_by_id(sku)
    return jsonify({'id': p.id, 'name': p.name, 'quantity': p.quantity}) if p else (jsonify({'error': 'Not found'}), 404)

@app.route('/api/reposicao/<sku>', methods=['GET'])
def get_picking_info(sku):
    res = container.use_case.get_picking_info(sku)
    return jsonify(res.value) if res.is_success else (jsonify({'error': res.error}), 404)

@app.route('/api/produto', methods=['POST'])
def create_produto():
    data = request.json
    res = container.use_case.create_product(data['id'], data['name'])
    return (jsonify({'message': 'OK'}), 201) if res.is_success else (jsonify({'error': res.error}), 400)

@app.route('/api/entrada', methods=['POST'])
def add_stock():
    data = request.json
    res = container.use_case.execute_add(data['id'], data['amount'], data.get('expiration_date', ''), data.get('batch_code', ''))
    return (jsonify({'message': 'OK'}), 200) if res.is_success else (jsonify({'error': res.error}), 400)

@app.route('/api/saida', methods=['POST'])
def remove_stock():
    data = request.json
    res = container.use_case.execute_remove(data['id'], data['amount'])
    return (jsonify({'message': 'OK'}), 200) if res.is_success else (jsonify({'error': res.error}), 400)

@app.route('/api/historico', methods=['GET'])
def get_historico(): return jsonify(container.use_case.get_recent_history())

if __name__ == '__main__':
    is_dev = (container.config.ENV == 'development')
    app.run(host=container.config.HOST, port=container.config.PORT, debug=is_dev)
EOF

kippe::step 3 ${TOTAL_STEPS} "Aligning Test Suite with IoC Architecture..."
cat << 'EOF' > "${KIPPE_ROOT}/tests/test_api.py"
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
EOF

kippe::step 4 ${TOTAL_STEPS} "Validating Composition and Architecture..."
kippe::test_execute_all

kippe::step 5 ${TOTAL_STEPS} "Gate A Review and Documentation..."
cat << 'EOF' > ESTADO_PROJETO.md
# 🌐 KIPPE PLATFORM: Institutional Retail Operations

## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 2 (Profissional).

## 2. Status Executivo
* **Programa Atual:** PROGRAMA B (Identity & Security)
* **Gate Transposto:** [ GATE A - FOUNDATION READY ] ✅
* **Última Entrega:** Sprint A005 (IoC Dependency Injection Container)

## 3. Diretórios e Artefatos Essenciais
* `data/` - (Fronteira de persistência SQLite determinística)
* `docs/architecture/MANIFESTO.md` - (Constituição da Plataforma)
* `src/infrastructure/config.py` - (12-Factor App Environment Layer)
* `src/infrastructure/container.py` - (Dependency Injection IoC Engine)
* `reports/logs/` - (Audit Trails e Observabilidade de Plataforma)

## 4. Próxima Ação Requerida
* **GATE A APPROVED.** Iniciar **Programa B (Identity & Security)** com a **Sprint SEC001 (Identidade e Autenticação)**. A fundação imutável agora exigirá controle de quem está utilizando os Handlers (APIs). Precisamos introduzir rastreabilidade de Operador via PIN numérico para garantir auditoria nominal no chão de loja.
EOF

kippe::checkpoint_create \
    "006" \
    "1.0.0" \
    "A005" \
    "SUCCESS"

kippe::manifest_create \
    "A005" \
    "A" \
    "1.0.0" \
    "SUCCESS" \
    "SEC001"

kippe::step 6 ${TOTAL_STEPS} "Committing Foundation Closure..."
git add src/infrastructure/container.py app.py tests/test_api.py ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_A005.json
git commit -m "feat(infra): implementa IoC container, resolve dependencias e atinge Gate A" || true

kippe::banner_finish
kippe::success "Dependency Injection Container implemented. GATE A APPROVED."
echo -e "\n============================================="
echo -e "   [ GATE A - FOUNDATION READY ] APPROVED"
echo -e "============================================="
echo -e "\nNext Program: B (Identity & Security)"
echo -e "Next Sprint: SEC001 (Operator Identity)\n"

