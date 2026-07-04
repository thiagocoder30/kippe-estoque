import sqlite3
import pickle
import os
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.domain.warehouse.ledger import InventoryAccount

class SQLiteCatalog:
    """
    Repositório de Catálogo persistente em SQLite.
    Armazena os dados mestres dos produtos (SKU, Nome, Categoria).
    """
    def __init__(self, db_path="kippe.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS catalog
                            (sku TEXT PRIMARY KEY, description TEXT, brand TEXT, category TEXT)''')

    def register_product(self, sku, description, category):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO catalog (sku, description, brand, category) VALUES (?, ?, ?, ?)",
                (sku, description, "Genérica", category)
            )

    def get_by_sku(self, sku):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT description, brand, category FROM catalog WHERE sku = ?", (sku,))
            row = cursor.fetchone()
            
        # Simula o objeto Product esperado pelo sistema
        class Product: pass
        p = Product()
        if row:
            p.description, p.brand, p.category = row
        else:
            p.description = "Produto Sem Cadastro"
            p.brand = "N/A"
            p.category = "GERAL"
        return p

class SQLiteLedgerRepo(InventoryAccountRepository):
    """
    Repositório de Event Sourcing persistente em SQLite.
    Utiliza serialização binária (pickle) para salvar o Agregado de Domínio intacto,
    garantindo que as 174 regras de negócio e testes não quebrem.
    """
    def __init__(self, db_path="kippe.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS ledger
                            (sku TEXT PRIMARY KEY, data BLOB)''')

    def save(self, account: InventoryAccount) -> None:
        # Serializa o objeto Python inteiro (com todas as suas entradas de Ledger)
        data = pickle.dumps(account)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO ledger (sku, data) VALUES (?, ?)", (account.sku, data))

    def get_by_sku(self, sku: str) -> InventoryAccount:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT data FROM ledger WHERE sku = ?", (sku,))
            row = cursor.fetchone()
            if row:
                # Deserializa e reconstrói o objeto exato do domínio
                return pickle.loads(row[0])
            return None
    
    def get_all(self):
        accounts = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT data FROM ledger")
            for row in cursor.fetchall():
                accounts.append(pickle.loads(row[0]))
        return accounts

