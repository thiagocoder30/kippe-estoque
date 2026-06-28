import sqlite3
from typing import Optional
from src.domain.snapshot import InventorySnapshot
class SQLiteSnapshotRepository:
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
                CREATE TABLE IF NOT EXISTS inventory_snapshots (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            ''')
            conn.commit()
    def save(self, snapshot: InventorySnapshot) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO inventory_snapshots (id, payload, created_by, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (snapshot.id, snapshot.payload, snapshot.created_by, snapshot.timestamp))
            conn.commit()
    def get_by_id(self, snapshot_id: str) -> Optional[InventorySnapshot]:
        with self._get_connection() as conn:
            row = conn.execute('SELECT * FROM inventory_snapshots WHERE id = ?', (snapshot_id,)).fetchone()
            if not row: return None
            r_dict = dict(row)
            return InventorySnapshot(
                id=r_dict['id'],
                payload=r_dict['payload'],
                created_by=r_dict['created_by'],
                timestamp=r_dict['timestamp']
            )
