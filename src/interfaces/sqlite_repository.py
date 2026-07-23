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
                ''', (product.id, batch.code, batch.expiration_date, batch.quantity, batch.manufacturing_date, batch.supplier, batch.status, batch.traceability_id, batch.location_id, batch.warehouse_id, float(getattr(batch, 'cost_per_unit', 0.0))))
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

    def get_dashboard_projection(self, sku_or_barcode: str) -> dict:
        import sqlite3
        try:
            conn = sqlite3.connect('kippe.db')
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            # 1. Catálogo: Busca tanto por SKU quanto por Código de Barras
            cur.execute("SELECT * FROM catalog WHERE sku = ? OR barcode = ?", (sku_or_barcode, sku_or_barcode))
            catalog_row = cur.fetchone()
            
            if not catalog_row:
                conn.close()
                return None
                
            catalog_data = dict(catalog_row)
            
            # O Segredo: Pegamos o SKU verdadeiro (ex: MAT-1023) para as próximas buscas
            true_sku = catalog_data.get('sku', sku_or_barcode)
            
            # 2. Lotes e Saldos usando o verdadeiro SKU
            cur.execute("SELECT * FROM batches WHERE sku = ?", (true_sku,))
            batches_rows = cur.fetchall()
            
            batches = []
            total_quantity = 0
            primary_supplier = "N/D"
            
            for b in batches_rows:
                b_dict = dict(b)
                qty = int(b_dict.get('quantity') or 0)
                store_qty = int(b_dict.get('quantity_store') or 0)
                bal_qty = int(b_dict.get('store_balance') or 0)
                
                batches.append({
                    "batch_code": b_dict.get('batch_code', 'N/D'),
                    "quantity": qty,
                    "expiration_date": b_dict.get('expiration', 'N/D')
                })
                total_quantity += (qty + store_qty + bal_qty)
                
                if b_dict.get('supplier') and primary_supplier == "N/D":
                    primary_supplier = b_dict.get('supplier')
                    
            # 3. Auditoria (Últimas Movimentações)
            cur.execute("SELECT * FROM audit_log WHERE sku = ? ORDER BY timestamp DESC LIMIT 10", (true_sku,))
            audit_rows = cur.fetchall()
            
            audit_logs = []
            for a in audit_rows:
                a_dict = dict(a)
                audit_logs.append({
                    "date": a_dict.get('timestamp', ''),
                    "op": a_dict.get('operation', ''),
                    "qty": a_dict.get('quantity', 0),
                    "operator": a_dict.get('operator', 'SISTEMA')
                })
                
            conn.close()
            
            return {
                "sku": true_sku,
                "description": catalog_data.get('description', 'PRODUTO SEM NOME'),
                "barcode": catalog_data.get('barcode', true_sku),
                "category": catalog_data.get('category', 'N/D'),
                "photo": catalog_data.get('photo', None),
                "balances": {
                    "total": total_quantity
                },
                "primary_supplier": primary_supplier,
                "physical_location": {
                    "details": catalog_data.get('box_location', 'NÃO ENDEREÇADO')
                },
                "traceability": {
                    "batches": batches
                },
                "audit_logs": audit_logs
            }
            
        except Exception as e:
            print(f"Erro no Read Model do sku/ean {sku_or_barcode}: {e}")
            return None
