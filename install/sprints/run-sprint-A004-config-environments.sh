#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A: FOUNDATION
# SPRINT A004
# CONFIGURATION & ENVIRONMENTS (12-Factor App)
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
    "A004" \
    "Configuration & Environments"

kippe::step 1 ${TOTAL_STEPS} "Building Configuration Layer (12-Factor)..."
cat << 'EOF' > "${KIPPE_ROOT}/src/infrastructure/config.py"
import os

class Config:
    """
    Resolution Layer para configurações de ambiente.
    Remove todos os hardcodes da plataforma e centraliza a injeção.
    """
    def __init__(self):
        # Ambiente (development, testing, production)
        self.ENV = os.environ.get("KIPPE_ENV", "development")
        
        # Persistência
        self.DB_PATH = os.environ.get("KIPPE_DB_PATH", "data/estoque_producao.db")
        
        # Observabilidade
        self.LOG_PATH = os.environ.get("KIPPE_LOG_PATH", "reports/logs/app.log")
        
        # Rede / Bind
        self.HOST = os.environ.get("KIPPE_HOST", "0.0.0.0")
        self.PORT = int(os.environ.get("KIPPE_PORT", 5000))

    @classmethod
    def for_testing(cls):
        """Factory para forçar ambiente de teste de forma estrita."""
        os.environ["KIPPE_ENV"] = "testing"
        os.environ["KIPPE_DB_PATH"] = "data/test_strict.db"
        os.environ["KIPPE_LOG_PATH"] = "data/test_strict.log"
        return cls()
EOF

kippe::step 2 ${TOTAL_STEPS} "Establishing Environment Defaults (.env.example)..."
cat << 'EOF' > "${KIPPE_ROOT}/.env.example"
# KIPPE PLATFORM - ENVIRONMENT CONFIGURATION
# Copie este arquivo para .env em produção

KIPPE_ENV=production
KIPPE_DB_PATH=data/estoque_producao.db
KIPPE_LOG_PATH=reports/logs/app.log
KIPPE_HOST=0.0.0.0
KIPPE_PORT=8080
EOF

if ! grep -q "\.env" "${KIPPE_ROOT}/.gitignore" 2>/dev/null; then
    echo ".env" >> "${KIPPE_ROOT}/.gitignore"
fi

kippe::step 3 ${TOTAL_STEPS} "Refactoring Application Entrypoint (app.py)..."
cat << 'EOF' > "${KIPPE_ROOT}/app.py"
import os
from flask import Flask, jsonify, request, render_template
from src.infrastructure.config import Config
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.use_cases.manage_stock import ManageStockUseCase
from src.infrastructure.logger_adapter import FileLogger

# Inicializa a camada de resolução de ambiente
cfg = Config()

app = Flask(__name__)
# Injeta as dependências via Config
repo = SQLiteProductRepository(cfg.DB_PATH)
sys_logger = FileLogger(cfg.LOG_PATH)
uc = ManageStockUseCase(repository=repo, logger=sys_logger)

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/produtos', methods=['GET'])
def get_produtos():
    return jsonify([{
        'id': p.id, 'name': p.name, 'quantity': p.quantity
    } for p in uc.list_all()])

@app.route('/api/produto/<sku>', methods=['GET'])
def get_produto(sku):
    p = repo.get_by_id(sku)
    return jsonify({'id': p.id, 'name': p.name, 'quantity': p.quantity}) if p else (jsonify({'error': 'Not found'}), 404)

@app.route('/api/reposicao/<sku>', methods=['GET'])
def get_picking_info(sku):
    res = uc.get_picking_info(sku)
    return jsonify(res.value) if res.is_success else (jsonify({'error': res.error}), 404)

@app.route('/api/produto', methods=['POST'])
def create_produto():
    data = request.json
    res = uc.create_product(data['id'], data['name'])
    return (jsonify({'message': 'OK'}), 201) if res.is_success else (jsonify({'error': res.error}), 400)

@app.route('/api/entrada', methods=['POST'])
def add_stock():
    data = request.json
    res = uc.execute_add(data['id'], data['amount'], data.get('expiration_date', ''), data.get('batch_code', ''))
    return (jsonify({'message': 'OK'}), 200) if res.is_success else (jsonify({'error': res.error}), 400)

@app.route('/api/saida', methods=['POST'])
def remove_stock():
    data = request.json
    res = uc.execute_remove(data['id'], data['amount'])
    return (jsonify({'message': 'OK'}), 200) if res.is_success else (jsonify({'error': res.error}), 400)

@app.route('/api/historico', methods=['GET'])
def get_historico(): return jsonify(uc.get_recent_history())

if __name__ == '__main__':
    # Controle de debug estrito baseado no ambiente
    is_dev = (cfg.ENV == 'development')
    app.run(host=cfg.HOST, port=cfg.PORT, debug=is_dev)
EOF

kippe::step 4 ${TOTAL_STEPS} "Validating Configuration Layer Integration..."
# Adiciona um teste rápido para garantir a injeção
cat << 'EOF' > "${KIPPE_ROOT}/tests/test_config.py"
import os
from src.infrastructure.config import Config

def test_config_default_resolution():
    if "KIPPE_ENV" in os.environ: del os.environ["KIPPE_ENV"]
    cfg = Config()
    assert cfg.ENV == "development"
    assert cfg.PORT == 5000

def test_config_strict_testing_factory():
    cfg = Config.for_testing()
    assert cfg.ENV == "testing"
    assert "test_strict.db" in cfg.DB_PATH
EOF

kippe::test_execute_all

kippe::step 5 ${TOTAL_STEPS} "Updating Governance and Committing..."
cat << 'EOF' > ESTADO_PROJETO.md
# 🌐 KIPPE PLATFORM: Institutional Retail Operations

## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 2 (Profissional).

## 2. Status Executivo
* **Programa Atual:** PROGRAMA A (Foundation)
* **Gate Alvo:** GATE A - Foundation Ready
* **Última Entrega:** Sprint A004 (Configuration & Environments)

## 3. Diretórios e Artefatos Essenciais
* `data/` - (Fronteira de persistência SQLite)
* `docs/architecture/MANIFESTO.md` - (Constituição do Sistema)
* `src/infrastructure/config.py` - (12-Factor App Configuration Layer)
* `.env.example` - (Gabarito de Ambientes)

## 4. Próxima Ação Requerida
* **Sprint A005 (Dependency Injection Container):** A configuração agora está extraída, mas a injeção em `app.py` continua manual (`repo = ...`, `uc = ...`). Vamos institucionalizar o "Bootstrapping" do core implementando um Contêiner de Injeção de Dependências puro, nos aproximando do almejado GATE A.
EOF

kippe::checkpoint_create \
    "005" \
    "1.0.0" \
    "A004" \
    "SUCCESS"

kippe::manifest_create \
    "A004" \
    "A" \
    "1.0.0" \
    "SUCCESS" \
    "A005"

kippe::step 6 ${TOTAL_STEPS} "Committing Fixes..."
git add src/infrastructure/config.py app.py .env.example .gitignore ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_A004.json tests/test_config.py
git commit -m "feat(infra): implementa config layer 12-factor e isola variaveis de ambiente" || true

kippe::banner_finish
kippe::success "Configuration Layer successfully deployed."
echo -e "\nNext Sprint: A005 (Dependency Injection Container)\n"

