#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A: FOUNDATION
# SPRINT A003
# EVENTOS & OBSERVABILIDADE
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
    "A" \
    "A003" \
    "Eventos & Observabilidade"

kippe::step 1 ${TOTAL_STEPS} "Creating Logger Interface (Port)..."
mkdir -p "${KIPPE_ROOT}/src/interfaces"
cat << 'EOF' > "${KIPPE_ROOT}/src/interfaces/logger.py"
from typing import Protocol

class Logger(Protocol):
    """
    Contrato de Observabilidade.
    Garante que as regras de negócio desconheçam a biblioteca de logging utilizada.
    """
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
EOF

kippe::step 2 ${TOTAL_STEPS} "Creating FileLogger Adapter (Infrastructure)..."
mkdir -p "${KIPPE_ROOT}/src/infrastructure"
touch "${KIPPE_ROOT}/src/infrastructure/__init__.py"

cat << 'EOF' > "${KIPPE_ROOT}/src/infrastructure/logger_adapter.py"
import logging
import os
from src.interfaces.logger import Logger

class FileLogger:
    """
    Adapter concreto para gravação de logs institucionais.
    """
    def __init__(self, log_file: str = "reports/logs/app.log"):
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        self.logger = logging.getLogger("KIPPE_CORE")
        self.logger.setLevel(logging.INFO)
        
        # Evita duplicação de handlers durante a injeção em testes
        if not self.logger.handlers:
            formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def info(self, message: str) -> None:
        self.logger.info(message)

    def warning(self, message: str) -> None:
        self.logger.warning(message)

    def error(self, message: str) -> None:
        self.logger.error(message)
EOF

kippe::step 3 ${TOTAL_STEPS} "Injecting Logger into Use Cases..."
cat << 'EOF' > "${KIPPE_ROOT}/src/use_cases/manage_stock.py"
from typing import List, Dict, Any, Optional
from src.domain.product import Product
from src.domain.result import Result
from src.interfaces.logger import Logger

class ManageStockUseCase:
    def __init__(self, repository, logger: Optional[Logger] = None):
        self.repository = repository
        self.logger = logger

    def _log_info(self, msg: str):
        if self.logger: self.logger.info(msg)
        
    def _log_warn(self, msg: str):
        if self.logger: self.logger.warning(msg)

    def create_product(self, product_id: str, name: str) -> Result[None, str]:
        if self.repository.get_by_id(product_id):
            self._log_warn(f"Cadastro Bloqueado: SKU [{product_id}] já existe no sistema.")
            return Result.fail("Produto já cadastrado.")
            
        product = Product(id=product_id, name=name, quantity=0)
        self.repository.save(product)
        self._log_info(f"Produto Criado: SKU [{product_id}] - {name}")
        return Result.ok(None)

    def execute_add(self, product_id: str, amount: int, expiration_date: str, batch_code: str) -> Result[None, str]:
        product = self.repository.get_by_id(product_id)
        if not product: 
            self._log_warn(f"Entrada Bloqueada: SKU [{product_id}] não encontrado.")
            return Result.fail("Produto não encontrado.")
            
        res = product.add_stock(amount, expiration_date, batch_code)
        if res.is_success:
            self.repository.save(product)
            self.repository.log_transaction(product_id, f'ENTRADA (Lote {batch_code})', amount)
            self._log_info(f"Entrada Registrada: SKU [{product_id}] | Lote [{batch_code}] | Qtd: {amount}")
        else:
            self._log_warn(f"Entrada Rejeitada pelo FEFO: SKU [{product_id}] - {res.error}")
            
        return res

    def execute_remove(self, product_id: str, amount: int) -> Result[None, str]:
        product = self.repository.get_by_id(product_id)
        if not product: 
            self._log_warn(f"Saída Bloqueada: SKU [{product_id}] não encontrado.")
            return Result.fail("Produto não encontrado.")
            
        res = product.remove_stock(amount)
        if res.is_success:
            self.repository.save(product)
            self.repository.log_transaction(product_id, 'SAIDA (Baixa Automática FEFO)', amount)
            self._log_info(f"Saída Registrada (FEFO): SKU [{product_id}] | Qtd: {amount}")
        else:
            self._log_warn(f"Saída Rejeitada: SKU [{product_id}] - {res.error}")
            
        return res

    def list_all(self) -> List[Product]: 
        return self.repository.get_all()
    
    def get_picking_info(self, product_id: str) -> Result[Dict[str, Any], str]:
        product = self.repository.get_by_id(product_id)
        if not product: 
            self._log_warn(f"Gôndola (Ruptura/Falha): Consulta de Pick-List para SKU [{product_id}] inexistente.")
            return Result.fail("Produto sem cadastro.")
        
        info = {
            "name": product.name,
            "total_quantity": product.quantity,
            "instructions": product.get_picking_instructions()
        }
        return Result.ok(info)

    def get_recent_history(self) -> List[Dict[str, Any]]: 
        return self.repository.get_history()
EOF

kippe::step 4 ${TOTAL_STEPS} "Updating Application Entrypoint (app.py)..."
cat << 'EOF' > "${KIPPE_ROOT}/app.py"
from flask import Flask, jsonify, request, render_template
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.use_cases.manage_stock import ManageStockUseCase
from src.infrastructure.logger_adapter import FileLogger

app = Flask(__name__)
repo = SQLiteProductRepository("data/estoque_producao.db")
# Instancia o Logger Institucional apontando para o diretório de relatórios
sys_logger = FileLogger("reports/logs/app.log")
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
    app.run(host='0.0.0.0', port=5000, debug=False)
EOF

kippe::step 5 ${TOTAL_STEPS} "Writing Observability Test Suite..."
cat << 'EOF' > "${KIPPE_ROOT}/tests/test_observability.py"
import os
import pytest
from src.infrastructure.logger_adapter import FileLogger
from src.use_cases.manage_stock import ManageStockUseCase
from src.interfaces.sqlite_repository import SQLiteProductRepository

def test_logger_writes_to_file():
    log_file = "data/test_app.log"
    if os.path.exists(log_file): os.remove(log_file)
    
    logger = FileLogger(log_file)
    logger.info("Test Info Message")
    logger.warning("Test Warning Message")
    
    assert os.path.exists(log_file)
    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Test Info Message" in content
        assert "Test Warning Message" in content
        
    if os.path.exists(log_file): os.remove(log_file)
    
def test_use_case_logging_integration():
    db = "data/test_obs.db"
    log = "data/test_obs.log"
    repo = SQLiteProductRepository(db)
    logger = FileLogger(log)
    uc = ManageStockUseCase(repo, logger)
    
    # Aciona uma regra de negócio que deve ser barrada e logada
    uc.execute_add("SKU-FANTASMA", 10, "2030-12-31", "L01")
    
    with open(log, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Entrada Bloqueada: SKU [SKU-FANTASMA]" in content
        
    if os.path.exists(db): os.remove(db)
    if os.path.exists(log): os.remove(log)
EOF

kippe::step 6 ${TOTAL_STEPS} "Validating Architectural Integrity..."
kippe::test_execute_all

kippe::step 7 ${TOTAL_STEPS} "Updating Governance and Committing..."
cat << 'EOF' > ESTADO_PROJETO.md
# 🌐 KIPPE PLATFORM: Institutional Retail Operations

## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 1 (Funcional).

## 2. Status Executivo
* **Programa Atual:** PROGRAMA A (Foundation)
* **Gate Alvo:** GATE A - Foundation Ready
* **Última Entrega:** Sprint A003 (Eventos & Observabilidade)

## 3. Diretórios e Artefatos Essenciais
* `data/` - (Fronteira de persistência SQLite local)
* `docs/architecture/MANIFESTO.md` - (Constituição do Sistema)
* `install/sprints/` - (Motor CI arquivado e ativo)
* `reports/logs/app.log` - (NOVO: Log Institucional de Eventos da Plataforma)

## 4. Próxima Ação Requerida
* **Sprint A004 (Configuração & Ambientes):** Extrair hardcodes de caminhos (como portas e diretórios) introduzindo variáveis de ambiente (`.env`), deixando o projeto preparado para rodar dinamicamente em Produção vs Desenvolvimento.
EOF

kippe::checkpoint_create \
    "004" \
    "1.0.0" \
    "A003" \
    "SUCCESS"

kippe::manifest_create \
    "A003" \
    "A" \
    "1.0.0" \
    "SUCCESS" \
    "A004"

git add src/ app.py tests/ ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_A003.json
git commit -m "feat(core): implementa padrao adapter para observabilidade e logs imutaveis no dominio" || true

kippe::banner_finish
kippe::success "Observability module successfully integrated."
echo -e "\nNext Sprint: A004 (Configuration & Environment Variables)\n"

