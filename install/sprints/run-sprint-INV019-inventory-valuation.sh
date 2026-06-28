#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM C: INVENTORY
# SPRINT INV019: INVENTORY VALUATION (Read Model)
# ============================================================
set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"
# 1. Bootstrap
source install/lib/bootstrap.sh
source install/lib/testing.sh
source install/lib/validation.sh
kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR
TOTAL_STEPS=4
kippe::banner_program "C" "INV019" "Inventory Valuation"
kippe::step 1 ${TOTAL_STEPS} "Applying Domain Mutations: Batch Cost Extension & Repository Rewrite..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/sprints/patch_batch_cost.py"
import os
import sys
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor
def patch_batch_with_cost(content: str) -> str:
    if "cost_per_unit: float" not in content:
        content = content.replace(
            "location_id: str = ''",
            "location_id: str = ''\n    cost_per_unit: float = 0.0"
        )
    return content
try:
    with SafeRefactor("src/domain/batch.py") as sr:
        sr.apply(patch_batch_with_cost)
except Exception as e:
    print(f"Abortando mutação: {e}")
    sys.exit(1)
KIPPE_HUNK
python3 "${KIPPE_ROOT}/install/sprints/patch_batch_cost.py"
# Reconstrução integral do SQLite Repository para zero risco de indentação SQL/Python
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
                    allow_negative_stock INTEGER NOT NULL DEFAULT 0,
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
                    location_id TEXT DEFAULT '', warehouse_id TEXT DEFAULT 'WH-PADRAO', cost_per_unit REAL NOT NULL DEFAULT 0.0,
                    PRIMARY KEY (product_id, batch_code)
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS reservations (
                    id TEXT PRIMARY KEY, product_id TEXT NOT NULL, amount INTEGER NOT NULL,
                    operator_id TEXT NOT NULL, status TEXT NOT NULL, created_at DATETIME NOT NULL
                )
            ''')
            
            # Migrações retroativas
            cursor = conn.execute("PRAGMA table_info(products)")
            if 'allow_negative_stock' not in [info['name'] for info in cursor.fetchall()]:
                conn.execute("ALTER TABLE products ADD COLUMN allow_negative_stock INTEGER NOT NULL DEFAULT 0")
            cursor = conn.execute("PRAGMA table_info(batches)")
            if 'cost_per_unit' not in [info['name'] for info in cursor.fetchall()]:
                conn.execute("ALTER TABLE batches ADD COLUMN cost_per_unit REAL NOT NULL DEFAULT 0.0")
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
                INSERT INTO products (id, name, quantity, unit_of_measure, status, category_id, reserved_quantity, allow_negative_stock) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name, quantity=excluded.quantity, unit_of_measure=excluded.unit_of_measure, status=excluded.status, category_id=excluded.category_id, reserved_quantity=excluded.reserved_quantity, allow_negative_stock=excluded.allow_negative_stock
            ''', (product.id, product.name, product.quantity, product.unit_of_measure, product.status, product.category_id, product.reserved_quantity, int(product.allow_negative_stock)))
            
            conn.execute('DELETE FROM batches WHERE product_id = ?', (product.id,))
            for batch_code, batch in product.batches.items():
                conn.execute('''
                    INSERT INTO batches (product_id, batch_code, expiration_date, quantity, manufacturing_date, supplier, status, traceability_id, location_id, warehouse_id, cost_per_unit) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (product.id, batch.code, batch.expiration_date, batch.quantity, batch.manufacturing_date, batch.supplier, batch.status, batch.traceability_id, batch.location_id, batch.warehouse_id, float(batch.cost_per_unit)))
            conn.commit()
    def get_by_id(self, product_id: str) -> Optional[Product]:
        with self._get_connection() as conn:
            prod_row = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
            if not prod_row: return None
            
            batch_rows = conn.execute('SELECT * FROM batches WHERE product_id = ?', (product_id,)).fetchall()
            batches_dict = {}
            for row in batch_rows:
                r_dict = dict(row)
                batches_dict[r_dict['batch_code']] = Batch(
                    code=r_dict['batch_code'], product_id=r_dict['product_id'], quantity=r_dict['quantity'],
                    expiration_date=r_dict['expiration_date'], warehouse_id=r_dict.get('warehouse_id', 'WH-PADRAO'),
                    location_id=r_dict.get('location_id', ''), manufacturing_date=r_dict['manufacturing_date'],
                    supplier=r_dict['supplier'], status=r_dict['status'], traceability_id=r_dict['traceability_id'],
                    cost_per_unit=float(r_dict.get('cost_per_unit', 0.0))
                )
            product = Product(
                id=prod_row['id'], name=prod_row['name'], quantity=prod_row['quantity'], 
                batches=batches_dict, unit_of_measure=prod_row['unit_of_measure'], 
                status=prod_row['status'], category_id=prod_row['category_id'],
                allow_negative_stock=bool(dict(prod_row).get('allow_negative_stock', 0))
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
                    b_dict = dict(b)
                    batches_dict[b_dict['batch_code']] = Batch(
                        code=b_dict['batch_code'], product_id=b_dict['product_id'], quantity=b_dict['quantity'],
                        expiration_date=b_dict['expiration_date'], warehouse_id=b_dict.get('warehouse_id', 'WH-PADRAO'),
                        location_id=b_dict.get('location_id', ''), manufacturing_date=b_dict['manufacturing_date'],
                        supplier=b_dict['supplier'], status=b_dict['status'], traceability_id=b_dict['traceability_id'],
                        cost_per_unit=float(b_dict.get('cost_per_unit', 0.0))
                    )
                product = Product(
                    id=row['id'], name=row['name'], quantity=row['quantity'], 
                    batches=batches_dict, unit_of_measure=row['unit_of_measure'], 
                    status=row['status'], category_id=row['category_id'],
                    allow_negative_stock=bool(dict(row).get('allow_negative_stock', 0))
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
            return [dict(row) for row in rows]
KIPPE_HUNK
kippe::step 2 ${TOTAL_STEPS} "Injecting Valuation Domain Entities and Costing Engine..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/valuation.py"
from dataclasses import dataclass, field
from datetime import datetime
@dataclass(frozen=True)
class InventoryValuationResult:
    """
    Entidade: InventoryValuationResult (Read Model Imutável)
    Representa a fotografia financeira do estoque em um dado momento.
    """
    product_id: str
    total_quantity: int
    total_value: float
    average_cost: float
    valuation_method: str
    valuation_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
KIPPE_HUNK
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/services/inventory_valuation_engine.py"
from src.domain.product import Product
from src.domain.valuation import InventoryValuationResult
class InventoryValuationEngine:
    """
    Domain Service: InventoryValuationEngine
    Camada determinística de cálculo financeiro.
    Regra de Ouro: SÓ LÊ. Proibida a mutação do estoque ou dos lotes.
    """
    @staticmethod
    def calculate_valuation(product: Product, method: str = "FIFO") -> InventoryValuationResult:
        if method not in ["FIFO", "AVERAGE"]:
            raise ValueError(f"Método de valoração não suportado: {method}")
        total_qty = 0
        total_value = 0.0
        # Seleciona apenas os lotes físicos reais (ignora lotes virtuais de OVERDRAFT)
        valid_batches = [b for b in product.batches.values() if not b.code.startswith("OVERDRAFT") and b.quantity > 0]
        for batch in valid_batches:
            total_qty += batch.quantity
            total_value += (batch.quantity * batch.cost_per_unit)
        average_cost = total_value / total_qty if total_qty > 0 else 0.0
        return InventoryValuationResult(
            product_id=product.id,
            total_quantity=total_qty,
            total_value=total_value,
            average_cost=average_cost,
            valuation_method=method
        )
KIPPE_HUNK
# 3. Semantic Validator & 4. AST Compile
kippe::step 3 ${TOTAL_STEPS} "Verifying Code Integrity via Semantic and AST Gates..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
# 5. Regression Suite
kippe::step 4 ${TOTAL_STEPS} "Writing and Executing Financial Valuation Test Suite..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/test_inventory_valuation.py"
import pytest
from src.domain.product import Product
from src.domain.batch import Batch
from src.domain.services.inventory_valuation_engine import InventoryValuationEngine
def test_valuation_calculates_total_value_and_average_cost():
    p = Product(id="SKU-VAL-1", name="Óleo de Soja", quantity=150)
    
    p.batches["L-JAN"] = Batch(code="L-JAN", product_id="SKU-VAL-1", quantity=100, expiration_date="2030-01-01", cost_per_unit=5.00)
    p.batches["L-FEV"] = Batch(code="L-FEV", product_id="SKU-VAL-1", quantity=50, expiration_date="2030-02-01", cost_per_unit=8.00)
    
    result = InventoryValuationEngine.calculate_valuation(p, method="FIFO")
    
    assert result.total_quantity == 150
    assert result.total_value == (100 * 5.0) + (50 * 8.0)
    assert result.average_cost == 900 / 150
    assert result.valuation_method == "FIFO"
def test_valuation_ignores_overdraft_virtual_batches():
    p = Product(id="SKU-VAL-2", name="Açúcar", quantity=0)
    
    p.batches["L-1"] = Batch(code="L-1", product_id="SKU-VAL-2", quantity=10, expiration_date="2030-01-01", cost_per_unit=3.0)
    p.batches["OVERDRAFT-WH-1"] = Batch(code="OVERDRAFT-WH-1", product_id="SKU-VAL-2", quantity=-10, expiration_date="2099-12-31")
    
    result = InventoryValuationEngine.calculate_valuation(p)
    
    assert result.total_quantity == 10
    assert result.total_value == 30.0
def test_valuation_does_not_mutate_inventory_state():
    p = Product(id="SKU-VAL-3", name="Café", quantity=20)
    p.batches["L-1"] = Batch(code="L-1", product_id="SKU-VAL-3", quantity=20, expiration_date="2030-01-01", cost_per_unit=15.0)
    
    qty_before = p.quantity
    _ = InventoryValuationEngine.calculate_valuation(p)
    
    assert p.quantity == qty_before
KIPPE_HUNK
kippe::test_execute_all
# 6. Architecture Scorecard
cat << "SCORECARD" > "${KIPPE_ROOT}/docs/checkpoints/ARCHITECTURE_SCORECARD-INV019.md"
# Architecture Scorecard - Kippe Platform
### Sprint: INV019 - Inventory Valuation Engine

| Critério | Status | Detalhes |
| :--- | :--- | :--- |
| **Testes passando** | ✅ | GREEN. Valorações calculadas perfeitamente. |
| **Isolamento de Estado** | ✅ | \`InventoryValuationResult\` atua como um Read Model projetado e isolado. |
| **Integridade Operacional** | ✅ | Cálculo ignora sumariamente lotes de \`OVERDRAFT\` virtuais. |
| **Gate C.5 (Institutional)** | ✅ | Ponte arquitetural para o futuro Módulo Financeiro estabelecida. |

SCORECARD
# 7. Checkpoint & 8. Manifest
kippe::checkpoint_create "059" "1.3.0-frozen" "INV019" "SUCCESS"
kippe::manifest_create "INV019" "C" "1.3.0-frozen" "SUCCESS" "INV020"
# Limpeza de scripts de mutação
rm -f "${KIPPE_ROOT}"/install/sprints/patch_*.py
rm -f data/test_*.db data/test_*.log data/test_*.db-journal 2>/dev/null || true
# 9 a 12. Sincronização Compulsória do Estado Permanente
kippe::governance_sync \
    "C" \
    "Inventory" \
    "3" \
    "Institucional" \
    "C.5" \
    "Institutional Ready" \
    "INV019 (Inventory Valuation)" \
    "INV020 — Inventory Consolidation & Sign-off" \
    "19/20 Sprints" \
    "STABLE"
exit 0
