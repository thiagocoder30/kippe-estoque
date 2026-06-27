import sqlite3
from typing import List, Optional
from src.domain.product import Product
from src.interfaces.product_repository import ProductRepository

class SQLiteProductRepository:
    """
    Implementação concreta do repositório utilizando SQLite.
    Focado em operações O(1) para busca por ID e O(N) leve para listagem.
    """
    def __init__(self, db_path: str = "estoque_mercado.db"):
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
            conn.commit()

    def save(self, product: Product) -> None:
        """Salva ou atualiza um produto de forma atômica e idempotente."""
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO products (id, name, quantity) 
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET 
                    name=excluded.name, 
                    quantity=excluded.quantity
            ''', (product.id, product.name, product.quantity))
            conn.commit()

    def get_by_id(self, product_id: str) -> Optional[Product]:
        """Recupera a entidade de Domínio através do ID."""
        with self._get_connection() as conn:
            row = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
            if row:
                return Product(id=row['id'], name=row['name'], quantity=row['quantity'])
            return None

    def get_all(self) -> List[Product]:
        """Recupera todos os produtos cadastrados."""
        with self._get_connection() as conn:
            rows = conn.execute('SELECT * FROM products ORDER BY name').fetchall()
            return [Product(id=row['id'], name=row['name'], quantity=row['quantity']) for row in rows]
