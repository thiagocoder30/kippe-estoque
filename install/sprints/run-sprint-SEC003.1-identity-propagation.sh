#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM B: IDENTITY & SECURITY
# SPRINT SEC003.1 (HOTFIX ARCHITECTURE)
# NOMINAL CONTEXT INJECTION LAYER (Identity Propagation)
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

TOTAL_STEPS=7

kippe::banner_program \
    "B" \
    "SEC003.1" \
    "Identity Propagation Layer"

kippe::step 1 ${TOTAL_STEPS} "Defining Identity Provider Interface (Port)..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/interfaces/identity.py"
from typing import Protocol

class IdentityProvider(Protocol):
    """Contrato arquitetural para resolução de Identidade de Contexto."""
    def get_current_operator_id(self) -> str: ...
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Implementing Deterministic Context Resolver (Adapter)..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/identity.py"
from flask import has_request_context, request, session
from src.interfaces.identity import IdentityProvider

class CurrentOperatorResolver(IdentityProvider):
    """
    Adapter que resolve a identidade propagada através das fronteiras do sistema.
    Trata contextos web (Flask session) e contextos isolados de domínio (Testes/CLI).
    """
    def __init__(self, env: str):
        self.env = env
        self.override_id = None # Utilizado estritamente em sandboxes de testes isolados

    def get_current_operator_id(self) -> str:
        if self.override_id: 
            return self.override_id
            
        if has_request_context():
            # Test Security Bridge Injection
            if self.env == "testing" and "X-Test-Operator-Override" in request.headers:
                return request.headers.get("X-Test-Operator-Override")
            # Production AuthN Session
            return session.get('operator_id', 'SYSTEM')
            
        # Fallback de segurança para execuções assíncronas/CRON futuras
        return 'SYSTEM'
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Wiring Identity Provider into IoC Container..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/container.py"
from src.infrastructure.config import Config
from src.infrastructure.logger_adapter import FileLogger
from src.infrastructure.identity import CurrentOperatorResolver
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.interfaces.sqlite_operator_repository import SQLiteOperatorRepository
from src.use_cases.manage_stock import ManageStockUseCase
from src.use_cases.manage_operators import ManageOperatorsUseCase

class Container:
    def __init__(self, config_override: Config = None):
        self.config = config_override or Config()
        self._logger = None
        self._identity_provider = None
        
        self._product_repository = None
        self._operator_repository = None
        
        self._manage_stock_use_case = None
        self._manage_operators_use_case = None

    @property
    def logger(self) -> FileLogger:
        if not self._logger: self._logger = FileLogger(self.config.LOG_PATH)
        return self._logger

    @property
    def identity_provider(self) -> CurrentOperatorResolver:
        if not self._identity_provider: self._identity_provider = CurrentOperatorResolver(self.config.ENV)
        return self._identity_provider

    @property
    def product_repository(self) -> SQLiteProductRepository:
        if not self._product_repository: self._product_repository = SQLiteProductRepository(self.config.DB_PATH)
        return self._product_repository

    @property
    def operator_repository(self) -> SQLiteOperatorRepository:
        if not self._operator_repository: self._operator_repository = SQLiteOperatorRepository(self.config.DB_PATH)
        return self._operator_repository

    @property
    def use_case(self) -> ManageStockUseCase:
        if not self._manage_stock_use_case:
            self._manage_stock_use_case = ManageStockUseCase(
                repository=self.product_repository,
                logger=self.logger,
                identity_provider=self.identity_provider
            )
        return self._manage_stock_use_case
        
    @property
    def auth_use_case(self) -> ManageOperatorsUseCase:
        if not self._manage_operators_use_case:
            self._manage_operators_use_case = ManageOperatorsUseCase(
                repository=self.operator_repository,
                logger=self.logger
            )
        return self._manage_operators_use_case

    @property
    def repository(self) -> SQLiteProductRepository:
        return self.product_repository
KIPPE_HUNK

kippe::step 4 ${TOTAL_STEPS} "Refactoring Domain to Consume Auto-Injected Identity Context..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/use_cases/manage_stock.py"
from typing import List, Dict, Any, Optional
from src.domain.product import Product
from src.domain.result import Result
from src.interfaces.logger import Logger
from src.interfaces.identity import IdentityProvider

class ManageStockUseCase:
    def __init__(self, repository, logger: Optional[Logger] = None, identity_provider: Optional[IdentityProvider] = None):
        self.repository = repository
        self.logger = logger
        self.identity = identity_provider

    def _get_op(self) -> str:
        """Resolve a identidade automaticamente (Dependency Inversion)."""
        return self.identity.get_current_operator_id() if self.identity else 'SYSTEM'

    def _log_info(self, msg: str):
        if self.logger: self.logger.info(msg)
        
    def _log_warn(self, msg: str):
        if self.logger: self.logger.warning(msg)

    def create_product(self, product_id: str, name: str) -> Result[None, str]:
        op_id = self._get_op()
        if self.repository.get_by_id(product_id):
            self._log_warn(f"Cadastro Bloqueado: SKU [{product_id}] já existe. Operador: [{op_id}]")
            return Result.fail("Produto já cadastrado.")
            
        product = Product(id=product_id, name=name, quantity=0)
        self.repository.save(product)
        self.repository.log_transaction(product_id, 'CRIACAO DE PRODUTO', 0, op_id)
        self._log_info(f"Produto Criado: SKU [{product_id}] - {name}. Operador: [{op_id}]")
        return Result.ok(None)

    def execute_add(self, product_id: str, amount: int, expiration_date: str, batch_code: str) -> Result[None, str]:
        op_id = self._get_op()
        product = self.repository.get_by_id(product_id)
        if not product: 
            self._log_warn(f"Entrada Bloqueada: SKU [{product_id}] não encontrado. Operador: [{op_id}]")
            return Result.fail("Produto não encontrado.")
            
        res = product.add_stock(amount, expiration_date, batch_code)
        if res.is_success:
            self.repository.save(product)
            self.repository.log_transaction(product_id, f'ENTRADA (Lote {batch_code})', amount, op_id)
            self._log_info(f"Entrada Registrada: SKU [{product_id}] | Lote [{batch_code}] | Qtd: {amount}. Operador: [{op_id}]")
        else:
            self._log_warn(f"Entrada Rejeitada pelo FEFO: SKU [{product_id}] - {res.error}. Operador: [{op_id}]")
            
        return res

    def execute_remove(self, product_id: str, amount: int) -> Result[None, str]:
        op_id = self._get_op()
        product = self.repository.get_by_id(product_id)
        if not product: 
            self._log_warn(f"Saída Bloqueada: SKU [{product_id}] não encontrado. Operador: [{op_id}]")
            return Result.fail("Produto não encontrado.")
            
        res = product.remove_stock(amount)
        if res.is_success:
            self.repository.save(product)
            self.repository.log_transaction(product_id, 'SAIDA (Baixa Automática FEFO)', amount, op_id)
            self._log_info(f"Saída Registrada (FEFO): SKU [{product_id}] | Qtd: {amount}. Operador: [{op_id}]")
        else:
            self._log_warn(f"Saída Rejeitada: SKU [{product_id}] - {res.error}. Operador: [{op_id}]")
            
        return res

    def list_all(self) -> List[Product]: return self.repository.get_all()
    
    def get_picking_info(self, product_id: str) -> Result[Dict[str, Any], str]:
        product = self.repository.get_by_id(product_id)
        if not product: return Result.fail("Produto sem cadastro.")
        return Result.ok({"name": product.name, "total_quantity": product.quantity, "instructions": product.get_picking_instructions()})

    def get_recent_history(self) -> List[Dict[str, Any]]: return self.repository.get_history()
KIPPE_HUNK

kippe::step 5 ${TOTAL_STEPS} "Restoring API HTTP Error Standardization & Contracts..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/app.py"
from flask import Flask, jsonify, request, render_template, session
from src.infrastructure.container import Container

container = Container()
app = Flask(__name__)
app.secret_key = container.config.SECRET_KEY

def _has_valid_session():
    if container.config.ENV == "testing" and "X-Test-Operator-Override" in request.headers: return True
    return 'operator_id' in session

@app.route('/')
def index(): return render_template('index.html')

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

@app.route('/api/produtos', methods=['GET'])
def get_produtos():
    return jsonify([{'id': p.id, 'name': p.name, 'quantity': p.quantity} for p in container.use_case.list_all()])

@app.route('/api/produto/<sku>', methods=['GET'])
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
    res = container.use_case.create_product(data.get('id'), data.get('name'))
    return (jsonify({'message': 'OK'}), 201) if res.is_success else (jsonify({'error': res.error}), 400)

@app.route('/api/entrada', methods=['POST'])
def add_stock():
    if not _has_valid_session(): return jsonify({'error': 'Operador não autenticado.'}), 401
    data = request.json or {}
    res = container.use_case.execute_add(data.get('id'), data.get('amount'), data.get('expiration_date', ''), data.get('batch_code', ''))
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
KIPPE_HUNK

# Restaura assinaturas legadas nas suites de testes (Context Override via Container)
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/test_use_cases.py"
import pytest, os
from src.infrastructure.config import Config
from src.infrastructure.container import Container

@pytest.fixture
def use_case():
    cfg = Config.for_testing()
    c = Container(cfg)
    c.product_repository._init_db()
    with c.product_repository._get_connection() as conn:
        conn.execute('DELETE FROM products')
        conn.execute('DELETE FROM batches')
        conn.commit()
    # Mock direto na Identity Propagation Layer
    c.identity_provider.override_id = "TEST-OP"
    yield c.use_case
    if os.path.exists(cfg.DB_PATH): os.remove(cfg.DB_PATH)

def test_usecase_create_and_list(use_case):
    res = use_case.create_product("KPC-100", "Arroz 5kg")
    assert res.is_success is True
    assert len(use_case.list_all()) == 1

def test_usecase_add_stock(use_case):
    use_case.create_product("KPC-200", "Feijão")
    res = use_case.execute_add("KPC-200", 5, "2030-12-31", "LOTE-Y")
    assert res.is_success is True
    assert use_case.list_all()[0].quantity == 5

def test_usecase_remove_stock_fail(use_case):
    use_case.create_product("KPC-300", "Açúcar")
    use_case.execute_add("KPC-300", 5, "2030-12-31", "LOTE-Z")
    res = use_case.execute_remove("KPC-300", 10)
    assert res.is_success is False
KIPPE_HUNK

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/test_audit.py"
import pytest, os
from src.infrastructure.config import Config
from src.infrastructure.container import Container

@pytest.fixture
def test_ctx():
    cfg = Config.for_testing()
    c = Container(cfg)
    c.product_repository._init_db()
    with c.product_repository._get_connection() as conn:
        conn.execute('DELETE FROM products')
        conn.execute('DELETE FROM transactions')
        conn.commit()
    yield c
    if os.path.exists(cfg.DB_PATH): os.remove(cfg.DB_PATH)

def test_audit_trail_logging_with_identity(test_ctx):
    uc = test_ctx.use_case
    test_ctx.identity_provider.override_id = "OP-007"
    uc.create_product("CX-01", "Caixa Papelão")
    uc.execute_add("CX-01", 10, "2030-12-31", "LOTE-X") 
    
    # Simula troca de operador no contexto global
    test_ctx.identity_provider.override_id = "OP-009"
    uc.execute_remove("CX-01", 2)
    
    history = uc.get_recent_history()
    assert len(history) == 3 
    assert history[0]['amount'] == 2
    assert history[0]['operator_id'] == "OP-009"
    assert history[1]['amount'] == 10
    assert history[1]['operator_id'] == "OP-007"
KIPPE_HUNK

kippe::step 6 ${TOTAL_STEPS} "Validating Architectural Fix (Preflight & Regression)..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

kippe::step 7 ${TOTAL_STEPS} "Updating System Governance & Committing..."
cat << "KIPPE_HUNK" > ESTADO_PROJETO.md
# 🌐 KIPPE PLATFORM: Institutional Retail Operations

## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 2 (Profissional).

## 2. Status Executivo
* **Programa Atual:** PROGRAMA B (Identity & Security)
* **Gate Alvo:** GATE B - Security Ready
* **Última Entrega:** Sprint SEC003.1 (Identity Propagation Layer)

## 3. Diretórios e Artefatos Essenciais
* `src/infrastructure/identity.py` - (Nominal Context Resolver / Propagation Layer)
* `src/infrastructure/container.py` - (IoC Injetando Dependência de Contexto automaticamente)
* `src/use_cases/` - (Domínio agnóstico à infraestrutura web, resolvendo autoria via interface)

## 4. Próxima Ação Requerida
* **Sprint SEC004 (RBAC Gate Control):** Com a propagação de identidade operando de forma coesa (e os testes passando limpos), vamos estender a autoridade do Domínio de Estoque. Ações destrutivas passarão a consultar não apenas *quem* é o operador, mas *qual* é o seu `operator_role` (OPERADOR vs. GERENTE).
KIPPE_HUNK

kippe::checkpoint_create "014" "1.0.0" "SEC003.1" "SUCCESS"
kippe::manifest_create "SEC003.1" "B" "1.0.0" "SUCCESS" "SEC004"

git add src/ app.py tests/ ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_SEC003.1.json
git commit -m "fix(security): consolida Identity Propagation Layer e padroniza auth HTTP reestabelecendo contratos (SEC003.1)" || true

kippe::banner_finish
kippe::success "Identity Propagation Layer completed. Core Domain is fully aligned with Authentication boundaries."
echo -e "\nNext Sprint: SEC004 (RBAC Gate Control)\n"
exit 0

