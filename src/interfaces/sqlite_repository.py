import sqlite3
from typing import List, Optional, Dict, Any
from src.domain.product import Product

class SQLiteProductRepository:
    def __init__(self, db_path: str = "estoque_producao.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    quantity INTEGER NOT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
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
            conn.commit()

    def save(self, product: Product) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO products (id, name, quantity) 
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET 
                    name=excluded.name, quantity=excluded.quantity
            ''', (product.id, product.name, product.quantity))
            
            conn.execute('DELETE FROM batches WHERE product_id = ?', (product.id,))
            for batch_code, data in product.batches.items():
                conn.execute('''
                    INSERT INTO batches (product_id, batch_code, expiration_date, quantity) 
                    VALUES (?, ?, ?, ?)
                ''', (product.id, batch_code, data['exp'], data['qty']))
            conn.commit()

    def log_transaction(self, product_id: str, trans_type: str, amount: int) -> None:
        with self._get_connection() as conn:
            conn.execute('INSERT INTO transactions (product_id, type, amount) VALUES (?, ?, ?)', (product_id, trans_type, amount))
            conn.commit()

    def get_by_id(self, product_id: str) -> Optional[Product]:
        with self._get_connection() as conn:
            prod_row = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
            if not prod_row: return None
            
            batch_rows = conn.execute('SELECT batch_code, expiration_date, quantity FROM batches WHERE product_id = ?', (product_id,)).fetchall()
            batches_dict = {row['batch_code']: {'exp': row['expiration_date'], 'qty': row['quantity']} for row in batch_rows}
            
            return Product(id=prod_row['id'], name=prod_row['name'], quantity=prod_row['quantity'], batches=batches_dict)

    def get_all(self) -> List[Product]:
        with self._get_connection() as conn:
            rows = conn.execute('SELECT * FROM products ORDER BY name').fetchall()
            products = []
            for row in rows:
                batch_rows = conn.execute('SELECT batch_code, expiration_date, quantity FROM batches WHERE product_id = ? ORDER BY expiration_date', (row['id'],)).fetchall()
                batches_dict = {b['batch_code']: {'exp': b['expiration_date'], 'qty': b['quantity']} for b in batch_rows}
                products.append(Product(id=row['id'], name=row['name'], quantity=row['quantity'], batches=batches_dict))
            return products

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute('''
                SELECT t.id, t.type, t.amount, datetime(t.timestamp, 'localtime') as data, p.name 
                FROM transactions t
                JOIN products p ON t.product_id = p.id
                ORDER BY t.id DESC LIMIT ?
            ''', (limit,)).fetchall()
            return [dict(row) for row in rows]
