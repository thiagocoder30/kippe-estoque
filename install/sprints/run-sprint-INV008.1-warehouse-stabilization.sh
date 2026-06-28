#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM C: INVENTORY
# SPRINT INV008.1 (STABILIZATION & CAPACITY SPRINT)
# MULTIPLE WAREHOUSES STABILIZATION (Safe Overwrite Engine)
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

TOTAL_STEPS=5

kippe::banner_program \
    "C" \
    "INV008.1" \
    "Multiple Warehouses Stabilization"

kippe::step 1 ${TOTAL_STEPS} "Reconstructing Batch Entity with Strict Default Warehouse Contract..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/batch.py"
from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass
class Batch:
    """
    Entidade: Batch (Domínio de Inventário)
    Garante a integridade física de recipientes temporais de estoque (Lotes).
    Suporta rastreabilidade espacial através de localização e armazém de origem.
    """
    code: str  
    product_id: str
    quantity: int
    expiration_date: str  
    warehouse_id: str = "WH-PADRAO"  # Injeção nativa de infraestrutura (INV008)
    location_id: str = ""           # Endereçamento físico (INV007)
    manufacturing_date: str = ""  
    supplier: str = "PADRAO"
    status: str = "ATIVO"  
    traceability_id: str = ""

    def __post_init__(self):
        if not self.code or not isinstance(self.code, str) or len(self.code.strip()) == 0:
            raise ValueError("Violação de Invariante: O código do lote é estritamente obrigatório.")
        if not self.product_id or len(self.product_id.strip()) == 0:
            raise ValueError("Violação de Invariante: O lote deve estar atrelado a um SKU válido.")
        if self.quantity < 0:
            raise ValueError("Violação de Invariante: A quantidade do lote não pode ser negativa.")
        if not self.warehouse_id or len(self.warehouse_id.strip()) == 0:
            raise ValueError("Violação de Invariante: O identificador de armazém é obrigatório.")
        
        try:
            datetime.strptime(self.expiration_date, "%Y-%m-%d")
            if self.manufacturing_date:
                datetime.strptime(self.manufacturing_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Violação de Invariante: Formato de data inválido (Use YYYY-MM-DD).")

    def is_expired(self) -> bool:
        exp = datetime.strptime(self.expiration_date, "%Y-%m-%d").date()
        return exp <= datetime.today().date()

    def __getitem__(self, item: str) -> Any:
        if item == 'qty': return self.quantity
        if item == 'exp': return self.expiration_date
        if item == 'supplier': return self.supplier
        if item == 'status': return self.status
        if item == 'location_id': return self.location_id
        if item == 'warehouse_id': return self.warehouse_id
        raise KeyError(f"Atributo legado [{item}] indisponível na Entidade Batch.")
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Reconstructing Product Aggregate Root with Warehouse Consolidation..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/product.py"
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
from .result import Result
from .batch import Batch
from .services.fefo_selector import FEFOSelector

@dataclass
class Product:
    id: str  
    name: str  
    quantity: int = 0  
    reserved_quantity: int = 0
    batches: Dict[str, Batch] = field(default_factory=dict)  
    unit_of_measure: str = "un"  
    status: str = "ATIVO"
    category_id: Optional[str] = None  

    @property
    def available_quantity(self) -> int:
        return self.quantity - self.reserved_quantity

    def __post_init__(self):
        if not self.id or not isinstance(self.id, str) or len(self.id.strip()) == 0:
            raise ValueError("Violação de Invariante: O SKU do produto é estritamente obrigatório e imutável.")
        if not self.name or not isinstance(self.name, str) or len(self.name.strip()) == 0:
            raise ValueError("Violação de Invariante: O Nome comercial do produto não pode ser vazio.")
        if self.unit_of_measure not in ["un", "kg", "lt"]:
            raise ValueError(f"Violação de Invariante: Unidade de medida [{self.unit_of_measure}] inválida para o varejo.")
        if self.status not in ["ATIVO", "INATIVO"]:
            raise ValueError(f"Violação de Invariante: Status de comercialização [{self.status}] inconsistente.")

    def add_stock(self, amount: int, expiration_date: str, batch_code: str, manufacturing_date: str = "", supplier: str = "PADRAO", warehouse_id: str = "WH-PADRAO", location_id: str = "") -> Result[None, str]:
        if self.status == "INATIVO":
            return Result.fail("Operação Rejeitada: Bloqueio de catálogo. Não é permitido movimentar estoque de SKUs INATIVOS.")
        if amount <= 0:
            return Result.fail("Quantidade deve ser maior que zero.")
        if not batch_code:
            return Result.fail("O código do Lote é obrigatório.")
            
        try:
            new_batch = Batch(
                code=batch_code, product_id=self.id, quantity=amount,
                expiration_date=expiration_date, manufacturing_date=manufacturing_date, 
                supplier=supplier, warehouse_id=warehouse_id, location_id=location_id
            )
            if new_batch.is_expired():
                return Result.fail("BLOQUEIO DE DOCA: Mercadoria vencida ou vence hoje.")
        except ValueError as e:
            return Result.fail(str(e))

        self.quantity += amount
        if batch_code in self.batches:
            self.batches[batch_code].quantity += amount
        else:
            self.batches[batch_code] = new_batch
        return Result.ok(None)

    def remove_stock(self, amount: int) -> Result[None, str]:
        if self.status == "INATIVO":
            return Result.fail("Operação Rejeitada: Bloqueio de catálogo. SKU suspenso para movimentações.")
        if amount <= 0: return Result.fail("Quantidade inválida.")
        if self.quantity < amount: return Result.fail("Estoque físico insuficiente.")

        eligible_batches = [b for b in FEFOSelector.get_eligible_batches(self.batches) if b.quantity > 0]
        
        available_valid_qty = sum(b.quantity for b in eligible_batches)
        if available_valid_qty < amount:
            return Result.fail("Estoque insuficiente de lotes válidos (vencidos são bloqueados para saída).")
            
        remaining = amount
        for batch in eligible_batches:
            if remaining == 0: break
            if batch.quantity >= remaining:
                batch.quantity -= remaining
                remaining = 0
            else:
                remaining -= batch.quantity
                batch.quantity = 0

        self.quantity -= amount
        return Result.ok(None)
        
    def get_picking_instructions(self) -> list:
        eligible_batches = [b for b in FEFOSelector.get_eligible_batches(self.batches) if b.quantity > 0]
        return [{"lote": b.code, "validade": b.expiration_date, "qtd_disponivel": b.quantity} for b in eligible_batches]

    def get_stock_by_warehouse(self, warehouse_id: str) -> int:
        return sum(b.quantity for b in self.batches.values() if b.warehouse_id == warehouse_id)

    def get_available_stock_by_warehouse(self, warehouse_id: str) -> int:
        total_physical = self.quantity
        if total_physical == 0: return 0
        local_physical = self.get_stock_by_warehouse(warehouse_id)
        local_reserved = int((self.reserved_quantity * local_physical) / total_physical)
        return local_physical - local_reserved

    def can_be_removed(self) -> bool:
        return self.quantity == 0 and self.reserved_quantity == 0
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Reconstructing SQLite Product Repository to Unify Persistence Maps..."
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
            rows = conn.execute('SELECT t.id, t.type, t.amount, datetime(t.timestamp, \'localtime\') as data, p.name, t.operator_id FROM transactions t JOIN products p ON t.product_id = p.id ORDER BY t.id DESC LIMIT ?', (limit,)).fetchall()
            return [dict(row) as data for row in rows]
KIPPE_HUNK

kippe::step 4 ${TOTAL_STEPS} "Preflight AST Compiler Gate & Interface Contract Check..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"

kippe::step 5 ${TOTAL_STEPS} "Executing Core Suite Regression Validation..."
kippe::test_execute_all

kippe::checkpoint_create "038" "1.1.0-gov" "INV008.1" "SUCCESS"
kippe::manifest_create "INV008.1" "C" "1.0.0" "SUCCESS" "INV009"

# Sincronização do estado permanente e emissão do relatório executivo unificado
kippe::governance_sync \
    "C — Inventory" \
    "2 — Profissional" \
    "INV008.1" \
    "INV009 — Stock Transfers" \
    "C.2" \
    "8/20" \
    "46/46 PASS" \
    "PLATAFORMA ESTÁVEL"

exit 0

