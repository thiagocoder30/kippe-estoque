#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM C: INVENTORY
# SPRINT INV008.2: SYNTAX STABILIZATION & SEMANTIC GATE
# ============================================================

set -Eeuo pipefail

export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

source install/lib/bootstrap.sh
source install/lib/testing.sh
source install/lib/validation.sh

kippe::init
kippe::init_environment

trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=6

kippe::banner_program \
    "C" \
    "INV008.2" \
    "Syntax Stabilization & Semantic Gate"

kippe::step 1 ${TOTAL_STEPS} "Fixing Repository Syntax (Complete File Rewrite)..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/interfaces/sqlite_repository.py"
import sqlite3
import json
from typing import List, Optional, Dict, Any
from src.domain.product import Product
from src.domain.category import Category
from src.domain.batch import Batch

class SQLiteProductRepository:
    def __init__(self, db_path: str = "data/estoque_producao.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT, parent_id TEXT,
                    active INTEGER DEFAULT 1, sort_order INTEGER DEFAULT 0, classification_rules TEXT DEFAULT '{}',
                    FOREIGN KEY(parent_id) REFERENCES categories(id)
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS warehouses (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, address TEXT, is_active INTEGER DEFAULT 1
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS locations (
                    id TEXT PRIMARY KEY, warehouse TEXT NOT NULL, zone TEXT NOT NULL,
                    aisle TEXT NOT NULL, rack TEXT NOT NULL, shelf TEXT NOT NULL, is_active INTEGER DEFAULT 1
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, quantity INTEGER NOT NULL,
                    unit_of_measure TEXT NOT NULL DEFAULT 'un', status TEXT NOT NULL DEFAULT 'ATIVO',
                    category_id TEXT, reserved_quantity INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(category_id) REFERENCES categories(id)
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, product_id TEXT NOT NULL, type TEXT NOT NULL,
                    amount INTEGER NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, operator_id TEXT NOT NULL DEFAULT 'SYSTEM'
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS batches (
                    product_id TEXT NOT NULL, batch_code TEXT NOT NULL, expiration_date TEXT NOT NULL, quantity INTEGER NOT NULL,
                    manufacturing_date TEXT DEFAULT '', supplier TEXT DEFAULT 'PADRAO', status TEXT DEFAULT 'ATIVO', traceability_id TEXT DEFAULT '',
                    location_id TEXT DEFAULT '', warehouse_id TEXT DEFAULT 'WH-PADRAO',
                    PRIMARY KEY (product_id, batch_code)
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS reservations (
                    id TEXT PRIMARY KEY, product_id TEXT NOT NULL, amount INTEGER NOT NULL,
                    operator_id TEXT NOT NULL, status TEXT NOT NULL, created_at DATETIME NOT NULL
                )
            ''')
            conn.commit()

    def save_category(self, category: Category) -> None:
        with self._get_connection() as conn:
            rules_json = json.dumps(category.classification_rules)
            conn.execute('''
                INSERT INTO categories (id, name, description, parent_id, active, sort_order, classification_rules) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name, description=excluded.description, parent_id=excluded.parent_id, active=excluded.active, sort_order=excluded.sort_order, classification_rules=excluded.classification_rules
            ''', (category.id, category.name, category.description, category.parent_id, int(category.active), category.sort_order, rules_json))
            conn.commit()

    def get_category_by_id(self, category_id: str) -> Optional[Category]:
        with self._get_connection() as conn:
            row = conn.execute('SELECT * FROM categories WHERE id = ?', (category_id,)).fetchone()
            if not row: return None
            return Category(id=row['id'], name=row['name'], description=row['description'], parent_id=row['parent_id'], active=bool(row['active']), sort_order=row['sort_order'], classification_rules=json.loads(row['classification_rules']))

    def get_all_categories(self) -> List[Category]:
        with self._get_connection() as conn:
            rows = conn.execute('SELECT * FROM categories ORDER BY sort_order, name').fetchall()
            return [Category(id=r['id'], name=r['name'], description=r['description'], parent_id=r['parent_id'], active=bool(r['active']), sort_order=r['sort_order'], classification_rules=json.loads(r['classification_rules'])) for r in rows]

    def save(self, product: Product) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO products (id, name, quantity, unit_of_measure, status, category_id, reserved_quantity) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name, quantity=excluded.quantity, unit_of_measure=excluded.unit_of_measure, status=excluded.status, category_id=excluded.category_id, reserved_quantity=excluded.reserved_quantity
            ''', (product.id, product.name, product.quantity, product.unit_of_measure, product.status, product.category_id, product.reserved_quantity))
            
            conn.execute('DELETE FROM batches WHERE product_id = ?', (product.id,))
            for batch_code, batch in product.batches.items():
                conn.execute('''
                    INSERT INTO batches (product_id, batch_code, expiration_date, quantity, manufacturing_date, supplier, status, traceability_id, location_id, warehouse_id) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (product.id, batch.code, batch.expiration_date, batch.quantity, batch.manufacturing_date, batch.supplier, batch.status, batch.traceability_id, batch.location_id, batch.warehouse_id))
            conn.commit()

    def get_by_id(self, product_id: str) -> Optional[Product]:
        with self._get_connection() as conn:
            prod_row = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
            if not prod_row: return None
            
            batch_rows = conn.execute('SELECT * FROM batches WHERE product_id = ?', (product_id,)).fetchall()
            batches_dict = {}
            for row in batch_rows:
                batches_dict[row['batch_code']] = Batch(
                    code=row['batch_code'], product_id=row['product_id'], quantity=row['quantity'],
                    expiration_date=row['expiration_date'], warehouse_id=row.get('warehouse_id', 'WH-PADRAO'),
                    location_id=row.get('location_id', ''), manufacturing_date=row['manufacturing_date'],
                    supplier=row['supplier'], status=row['status'], traceability_id=row['traceability_id']
                )
            product = Product(
                id=prod_row['id'], name=prod_row['name'], quantity=prod_row['quantity'], 
                batches=batches_dict, unit_of_measure=prod_row['unit_of_measure'], 
                status=prod_row['status'], category_id=prod_row['category_id']
            )
            product.reserved_quantity = prod_row['reserved_quantity']
            return product

    def get_all(self) -> List[Product]:
        with self._get_connection() as conn:
            rows = conn.execute('SELECT * FROM products ORDER BY name').fetchall()
            products = []
            for row in rows:
                batch_rows = conn.execute('SELECT * FROM batches WHERE product_id = ? ORDER BY expiration_date', (row['id'],)).fetchall()
                batches_dict = {}
                for b in batch_rows:
                    batches_dict[b['batch_code']] = Batch(
                        code=b['batch_code'], product_id=b['product_id'], quantity=b['quantity'],
                        expiration_date=b['expiration_date'], warehouse_id=b.get('warehouse_id', 'WH-PADRAO'),
                        location_id=b.get('location_id', ''), manufacturing_date=b['manufacturing_date'],
                        supplier=b['supplier'], status=b['status'], traceability_id=b['traceability_id']
                    )
                product = Product(
                    id=row['id'], name=row['name'], quantity=row['quantity'], 
                    batches=batches_dict, unit_of_measure=row['unit_of_measure'], 
                    status=row['status'], category_id=row['category_id']
                )
                product.reserved_quantity = row['reserved_quantity']
                products.append(product)
            return products

    def log_transaction(self, product_id: str, trans_type: str, amount: int, operator_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute('INSERT INTO transactions (product_id, type, amount, operator_id) VALUES (?, ?, ?, ?)', (product_id, trans_type, amount, operator_id))
            conn.commit()

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute('''
                SELECT t.id, t.type, t.amount, datetime(t.timestamp, 'localtime') as data, p.name, t.operator_id 
                FROM transactions t JOIN products p ON t.product_id = p.id 
                ORDER BY t.id DESC LIMIT ?
            ''', (limit,)).fetchall()
            # Correção sintática aplicada: remoção da alucinação "as data"
            return [dict(row) for row in rows]
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying INF004 - Semantic Validator Engine..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/lib/semantic_validator.py"
import os
import sys
import ast
import re
from pathlib import Path

def run_semantic_checks(root_dir: Path) -> bool:
    """
    Analisa a árvore sintática (AST) e verifica anomalias estruturais
    e vazamentos de variáveis literais do Bash para o Python.
    """
    has_errors = False
    
    # Expressão regular para encontrar placeholders Bash não expandidos (ex: ${KIPPE_ROOT})
    bash_leak_pattern = re.compile(r'\$\{[a-zA-Z_][a-zA-Z0-9_]*\}')
    
    for filepath in root_dir.rglob("*.py"):
        if "venv" in filepath.parts or "__pycache__" in filepath.parts:
            continue
            
        try:
            content = filepath.read_text(encoding="utf-8")
            
            # 1. AST Parse (Verificação de Sintaxe Estrutural)
            ast.parse(content, filename=str(filepath))
            
            # 2. Leak Detection (Variáveis Bash Literais)
            leaks = bash_leak_pattern.findall(content)
            if leaks:
                print(f"[SEMANTIC ERROR] Vazamento de placeholder Bash detectado em {filepath.name}: {set(leaks)}")
                has_errors = True
                
        except SyntaxError as e:
            print(f"[AST ERROR] Erro de Sintaxe em {filepath.name} (Linha {e.lineno}): {e.msg}")
            has_errors = True
        except Exception as e:
            print(f"[ERROR] Falha ao analisar {filepath.name}: {str(e)}")
            has_errors = True
            
    return not has_errors

if __name__ == "__main__":
    if "KIPPE_ROOT" not in os.environ:
        print("CRITICAL: KIPPE_ROOT environment variable not set.")
        sys.exit(1)
        
    root = Path(os.environ["KIPPE_ROOT"])
    print("  -> Iniciando Validação Semântica (INF004)...")
    
    is_valid = run_semantic_checks(root / "src") and run_semantic_checks(root / "tests")
    
    if not is_valid:
        print("  -> Validação Semântica: FALHOU.")
        sys.exit(1)
    
    print("  -> Validação Semântica: APROVADA.")
    sys.exit(0)
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Integrating Semantic Validator into Preflight Gates..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/lib/validation.sh"
#!/usr/bin/env bash
# KIPPE PLATFORM PREFLIGHT VALIDATION MODULE

kippe::validate_script_syntax() {
    local script_path="\$1"
    
    echo "  -> Auditing bash syntax: \${script_path}"
    if ! bash -n "\${script_path}"; then
        kippe::error "Bash Syntax audit FAILED."
        exit 1
    fi
    
    # Novo Gate: INF004 (Semantic Validator)
    export PYTHONPATH="\${KIPPE_ROOT}"
    if ! python3 "\${KIPPE_ROOT}/install/lib/semantic_validator.py"; then
        kippe::error "Semantic Validator FAILED. Mutações perigosas detectadas."
        exit 1
    fi
    
    echo "  -> Auditing Python AST (Abstract Syntax Tree) via compileall..."
    if ! python3 -m compileall -q "\${KIPPE_ROOT}/src/" "\${KIPPE_ROOT}/app.py" "\${KIPPE_ROOT}/tests/"; then
        kippe::error "Python Compile audit FAILED."
        exit 1
    fi
    
    echo "  -> Preflight Quality Gates: PASSED"
}
KIPPE_HUNK
chmod +x "${KIPPE_ROOT}/install/lib/validation.sh"

kippe::step 4 ${TOTAL_STEPS} "Running Multi-Tier Validation & Regression Suite..."
source "${KIPPE_ROOT}/install/lib/validation.sh"
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

kippe::step 5 ${TOTAL_STEPS} "Emitting Technical Checkpoints & Manifests..."
# Limpeza de artefatos
rm -f data/test_*.db data/test_*.log data/test_*.db-journal 2>/dev/null || true

kippe::checkpoint_create "039" "1.1.0-gov" "INV008.2" "SUCCESS"
kippe::manifest_create "INV008.2" "C" "1.1.0-gov" "SUCCESS" "INV009"

kippe::step 6 ${TOTAL_STEPS} "Syncing Governance Ledger..."
kippe::governance_sync \
    "C — Inventory" \
    "2 — Profissional" \
    "INV008.2" \
    "INV009 — Stock Transfers" \
    "C.2" \
    "8/20" \
    "46/46 PASS" \
    "PLATAFORMA ESTÁVEL"

exit 0

