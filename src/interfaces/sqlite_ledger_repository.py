import sqlite3
from typing import List
from src.domain.ledger import LedgerEntry
class SQLiteLedgerRepository:
    """
    Adapter: SQLiteLedgerRepository
    Isola a responsabilidade de escrita do Livro-Razão (Append-Only).
    """
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
                CREATE TABLE IF NOT EXISTS inventory_ledger (
                    id TEXT PRIMARY KEY, product_id TEXT NOT NULL, event_type TEXT NOT NULL,
                    quantity_change INTEGER NOT NULL, quantity_before INTEGER NOT NULL,
                    quantity_after INTEGER NOT NULL, warehouse_id TEXT NOT NULL,
                    batch_code TEXT NOT NULL, operator_id TEXT NOT NULL,
                    reference_id TEXT, timestamp DATETIME NOT NULL
                )
            ''')
            conn.commit()
    def append(self, entry: LedgerEntry) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO inventory_ledger (
                    id, product_id, event_type, quantity_change, quantity_before,
                    quantity_after, warehouse_id, batch_code, operator_id,
                    reference_id, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry.id, entry.product_id, entry.event_type, entry.quantity_change,
                entry.quantity_before, entry.quantity_after, entry.warehouse_id,
                entry.batch_code, entry.operator_id, entry.reference_id, entry.timestamp
            ))
            conn.commit()
    def get_history_by_product(self, product_id: str) -> List[LedgerEntry]:
        with self._get_connection() as conn:
            rows = conn.execute('SELECT * FROM inventory_ledger WHERE product_id = ? ORDER BY timestamp ASC, id ASC', (product_id,)).fetchall()
            return [LedgerEntry(
                id=dict(r)['id'], product_id=dict(r)['product_id'], event_type=dict(r)['event_type'],
                quantity_change=dict(r)['quantity_change'], quantity_before=dict(r)['quantity_before'],
                quantity_after=dict(r)['quantity_after'], warehouse_id=dict(r)['warehouse_id'],
                batch_code=dict(r)['batch_code'], operator_id=dict(r)['operator_id'],
                reference_id=dict(r)['reference_id'], timestamp=dict(r)['timestamp']
            ) for r in rows]
