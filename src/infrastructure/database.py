import sqlite3
import pickle
import os
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.domain.warehouse.ledger import InventoryAccount

class SQLiteCatalog:
    """
    Repositório de Catálogo persistente em SQLite.
    Armazena os dados mestres dos produtos (SKU, Nome, Categoria, Foto Base64).
    """
    def __init__(self, db_path="kippe.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Cria a tabela adicionando a coluna photo para auditoria visual enterprise
            conn.execute('''CREATE TABLE IF NOT EXISTS catalog
                            (sku TEXT PRIMARY KEY, description TEXT, brand TEXT, category TEXT, photo TEXT)''')
            
            # Migração amigável caso a coluna photo não exista de sprints anteriores
            try:
                conn.execute("ALTER TABLE catalog ADD COLUMN photo TEXT")
            except sqlite3.OperationalError:
                pass # Coluna já existe

    def register_product(self, sku, description, category, photo=None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO catalog (sku, description, brand, category, photo) VALUES (?, ?, ?, ?, ?)",
                (sku, description, "Genérica", category, photo)
            )

    def get_by_sku(self, sku):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT description, brand, category, photo FROM catalog WHERE sku = ?", (sku,))
            row = cursor.fetchone()
            
        class Product: pass
        p = Product()
        if row:
            p.description, p.brand, p.category, p.photo = row
        else:
            p.description = "Produto Sem Cadastro"
            p.brand = "N/A"
            p.category = "GERAL"
            p.photo = None
        return p

    def search_by_term(self, term: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT sku, description, photo FROM catalog WHERE sku LIKE ? OR description LIKE ? LIMIT 10", 
                (f'%{term}%', f'%{term}%')
            )
            results = []
            for row in cursor.fetchall():
                results.append({"sku": row[0], "description": row[1], "photo": row[2]})
            return results

class SQLiteLedgerRepo(InventoryAccountRepository):
    def __init__(self, db_path="kippe.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS ledger
                            (sku TEXT PRIMARY KEY, data BLOB)''')

    def save(self, account: InventoryAccount) -> None:
        data = pickle.dumps(account)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO ledger (sku, data) VALUES (?, ?)", (account.sku, data))

    def get_by_sku(self, sku: str) -> InventoryAccount:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT data FROM ledger WHERE sku = ?", (sku,))
            row = cursor.fetchone()
            if row:
                return pickle.loads(row[0])
            return None
    
    def get_all(self):
        accounts = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT data FROM ledger")
            for row in cursor.fetchall():
                accounts.append(pickle.loads(row[0]))
        return accounts

