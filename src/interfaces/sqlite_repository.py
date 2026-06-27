import sqlite3
import json
from typing import List, Optional, Dict, Any
from src.domain.product import Product
from src.domain.category import Category
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
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    parent_id TEXT,
                    active INTEGER DEFAULT 1,
                    sort_order INTEGER DEFAULT 0,
                    classification_rules TEXT DEFAULT '{}',
                    FOREIGN KEY(parent_id) REFERENCES categories(id)
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_of_measure TEXT NOT NULL DEFAULT 'un',
                    status TEXT NOT NULL DEFAULT 'ATIVO',
                    category_id TEXT,
                    FOREIGN KEY(category_id) REFERENCES categories(id)
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    operator_id TEXT NOT NULL DEFAULT 'SYSTEM'
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS batches (
                    product_id TEXT NOT NULL,
                    batch_code TEXT NOT NULL,
                    expiration_date TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    PRIMARY KEY (product_id, batch_code)
                )
            ''')
            
            cursor = conn.execute("PRAGMA table_info(products)")
            columns = [info['name'] for info in cursor.fetchall()]
            if 'unit_of_measure' not in columns:
                conn.execute("ALTER TABLE products ADD COLUMN unit_of_measure TEXT NOT NULL DEFAULT 'un'")
            if 'status' not in columns:
                conn.execute("ALTER TABLE products ADD COLUMN status TEXT NOT NULL DEFAULT 'ATIVO'")
            if 'category_id' not in columns:
                conn.execute("ALTER TABLE products ADD COLUMN category_id TEXT")
                
            conn.commit()
    def save_category(self, category: Category) -> None:
        with self._get_connection() as conn:
            rules_json = json.dumps(category.classification_rules)
            conn.execute('''
                INSERT INTO categories (id, name, description, parent_id, active, sort_order, classification_rules) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET 
                    name=excluded.name, description=excluded.description,
                    parent_id=excluded.parent_id, active=excluded.active,
                    sort_order=excluded.sort_order, classification_rules=excluded.classification_rules
            ''', (category.id, category.name, category.description, category.parent_id, 
                  int(category.active), category.sort_order, rules_json))
            conn.commit()
    def get_category_by_id(self, category_id: str) -> Optional[Category]:
        with self._get_connection() as conn:
            row = conn.execute('SELECT * FROM categories WHERE id = ?', (category_id,)).fetchone()
            if not row: return None
            return Category(
                id=row['id'], name=row['name'], description=row['description'],
                parent_id=row['parent_id'], active=bool(row['active']), 
                sort_order=row['sort_order'], classification_rules=json.loads(row['classification_rules'])
            )
    def get_all_categories(self) -> List[Category]:
        with self._get_connection() as conn:
            rows = conn.execute('SELECT * FROM categories ORDER BY sort_order, name').fetchall()
            return [Category(
                id=r['id'], name=r['name'], description=r['description'],
                parent_id=r['parent_id'], active=bool(r['active']), 
                sort_order=r['sort_order'], classification_rules=json.loads(r['classification_rules'])
            ) for r in rows]
    def save(self, product: Product) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO products (id, name, quantity, unit_of_measure, status, category_id) 
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET 
                    name=excluded.name, quantity=excluded.quantity,
                    unit_of_measure=excluded.unit_of_measure, status=excluded.status,
                    category_id=excluded.category_id
            ''', (product.id, product.name, product.quantity, product.unit_of_measure, product.status, product.category_id))
            
            conn.execute('DELETE FROM batches WHERE product_id = ?', (product.id,))
            for batch_code, data in product.batches.items():
                conn.execute('''
                    INSERT INTO batches (product_id, batch_code, expiration_date, quantity) 
                    VALUES (?, ?, ?, ?)
                ''', (product.id, batch_code, data['exp'], data['qty']))
            conn.commit()
    def get_by_id(self, product_id: str) -> Optional[Product]:
        with self._get_connection() as conn:
            prod_row = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
            if not prod_row: return None
            
            batch_rows = conn.execute('SELECT batch_code, expiration_date, quantity FROM batches WHERE product_id = ?', (product_id,)).fetchall()
            batches_dict = {row['batch_code']: {'exp': row['expiration_date'], 'qty': row['quantity']} for row in batch_rows}
            
            return Product(
                id=prod_row['id'], name=prod_row['name'], quantity=prod_row['quantity'], 
                batches=batches_dict, unit_of_measure=prod_row['unit_of_measure'],
                status=prod_row['status'], category_id=prod_row['category_id']
            )
    def get_all(self) -> List[Product]:
        with self._get_connection() as conn:
            rows = conn.execute('SELECT * FROM products ORDER BY name').fetchall()
            products = []
            for row in rows:
                batch_rows = conn.execute('SELECT batch_code, expiration_date, quantity FROM batches WHERE product_id = ? ORDER BY expiration_date', (row['id'],)).fetchall()
                batches_dict = {b['batch_code']: {'exp': b['expiration_date'], 'qty': b['quantity']} for b in batch_rows}
                products.append(Product(
                    id=row['id'], name=row['name'], quantity=row['quantity'], 
                    batches=batches_dict, unit_of_measure=row['unit_of_measure'],
                    status=row['status'], category_id=row['category_id']
                ))
            return products
    def log_transaction(self, product_id: str, trans_type: str, amount: int, operator_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute('INSERT INTO transactions (product_id, type, amount, operator_id) VALUES (?, ?, ?, ?)', 
                         (product_id, trans_type, amount, operator_id))
            conn.commit()
    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute('''
                SELECT t.id, t.type, t.amount, datetime(t.timestamp, 'localtime') as data, p.name, t.operator_id 
                FROM transactions t JOIN products p ON t.product_id = p.id
                ORDER BY t.id DESC LIMIT ?
            ''', (limit,)).fetchall()
            return [dict(row) for row in rows]
