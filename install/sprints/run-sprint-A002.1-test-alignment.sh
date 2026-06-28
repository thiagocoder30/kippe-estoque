#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A: FOUNDATION
# SPRINT A002.1 (HOTFIX)
# TEST SUITE ALIGNMENT & CI HARDENING
# ============================================================

set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${ROOT}"

export KIPPE_ROOT="${ROOT}"
export KIPPE_LOG_DIR="${ROOT}/reports/logs"

source install/lib/bootstrap.sh

kippe::init
kippe::init_environment

trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=4

kippe::banner_program \
    "A" \
    "A002.1" \
    "Test Alignment & CI Hardening"

kippe::step 1 ${TOTAL_STEPS} "Hardening Testing Framework (testing.sh)..."
cat << 'EOF' > install/lib/testing.sh
#!/usr/bin/env bash
# KIPPE PLATFORM TESTING MODULE
# Orchestrates automated validation to prevent regressions.

kippe::test_environment() {
    echo "  -> Validating test dependencies..."
    if ! command -v python &> /dev/null; then
        kippe::error "Python environment not found. Halting."
        exit 1
    fi
    if ! python -m pytest --version &> /dev/null; then
        kippe::error "Pytest not found. Halting."
        exit 1
    fi
}

kippe::test_run_core() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local test_log="${KIPPE_LOG_DIR}/test-core-${timestamp}.log"
    
    echo "  -> Running Core Domain Test Suite..."
    
    if [[ -d "${KIPPE_ROOT}/tests" ]]; then
        if ! python -m pytest "${KIPPE_ROOT}/tests/" -v > "${test_log}" 2>&1; then
            cat "${test_log}"
            kippe::error "Core Domain Tests FAILED. Architecture violation detected. Halting pipeline."
            # FIX: O exit 1 garante que o CI/CD pare IMEDIATAMENTE e não commite lixo.
            exit 1
        fi
        echo "  -> Core Domain Tests PASSED. Log saved to reports/logs."
    else
        echo "  -> No tests/ directory found yet. Skipping validation."
    fi
}

kippe::test_execute_all() {
    echo "[TEST SUITE INITIATED]"
    kippe::test_environment
    kippe::test_run_core
    echo "[TEST SUITE COMPLETED SUCCESSFULLY]"
}
EOF
chmod +x install/lib/testing.sh

kippe::step 2 ${TOTAL_STEPS} "Aligning Legacy Tests to the FEFO WMS Engine..."

# 2.1 Refatorando testes de Domínio
cat << 'EOF' > tests/test_domain.py
from src.domain.product import Product

def test_add_stock_success():
    p = Product(id="KPC-100", name="Arroz 5kg", quantity=0)
    res = p.add_stock(5, "2030-12-31", "LOTE-X")
    assert res.is_success is True
    assert p.quantity == 5
    assert p.batches["LOTE-X"]['qty'] == 5

def test_add_stock_fail_negative():
    p = Product(id="KPC-100", name="Arroz 5kg", quantity=0)
    res = p.add_stock(-2, "2030-12-31", "LOTE-X")
    assert res.is_success is False
    assert "maior que zero" in res.error

def test_remove_stock_success():
    p = Product(id="KPC-100", name="Arroz 5kg", quantity=0)
    p.add_stock(20, "2030-12-31", "LOTE-X")
    res = p.remove_stock(10)
    assert res.is_success is True
    assert p.quantity == 10

def test_remove_stock_fail_insufficient():
    p = Product(id="KPC-100", name="Arroz 5kg", quantity=0)
    p.add_stock(20, "2030-12-31", "LOTE-X")
    res = p.remove_stock(50)
    assert res.is_success is False
    assert p.quantity == 20
    assert "Estoque físico insuficiente." in res.error
EOF

# 2.2 Refatorando testes de Casos de Uso
cat << 'EOF' > tests/test_use_cases.py
import pytest
import os
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.use_cases.manage_stock import ManageStockUseCase

@pytest.fixture
def use_case():
    db_path = "data/test_usecase.db"
    repo = SQLiteProductRepository(db_path=db_path)
    with repo._get_connection() as conn:
        conn.execute('DELETE FROM products')
        conn.execute('DELETE FROM batches')
        conn.commit()
    yield ManageStockUseCase(repository=repo)
    if os.path.exists(db_path):
        os.remove(db_path)

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
    assert "Estoque físico insuficiente" in res.error
EOF

# 2.3 Refatorando testes da API
cat << 'EOF' > tests/test_api.py
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
EOF

# 2.4 Refatorando testes do Audit Trail
cat << 'EOF' > tests/test_audit.py
import pytest
import os
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.use_cases.manage_stock import ManageStockUseCase

@pytest.fixture
def repo():
    db = "data/test_audit.db"
    r = SQLiteProductRepository(db)
    yield r
    if os.path.exists(db):
        os.remove(db)

def test_audit_trail_logging(repo):
    uc = ManageStockUseCase(repo)
    uc.create_product("CX-01", "Caixa Papelão")
    uc.execute_add("CX-01", 10, "2030-12-31", "LOTE-X") # Gera Log de Entrada
    uc.execute_remove("CX-01", 2) # Gera Log de Saida
    
    history = uc.get_recent_history()
    
    assert len(history) == 2
    assert 'SAIDA' in history[0]['type'] 
    assert history[0]['amount'] == 2
    assert 'ENTRADA' in history[1]['type']
    assert history[1]['amount'] == 10
EOF

kippe::step 3 ${TOTAL_STEPS} "Re-Validating Architecture Integrity..."
source install/lib/testing.sh
kippe::test_execute_all

kippe::step 4 ${TOTAL_STEPS} "Committing Fixes..."
git add install/lib/testing.sh tests/
git commit -m "test(core): hardens CI abort mechanism and aligns legacy tests with FEFO engine" || true

kippe::banner_finish
kippe::success "Test Suite Rot eliminated. CI Pipeline is now strictly blocking."
echo -e "\nNext Sprint: A003 (Eventos & Observabilidade)\n"

