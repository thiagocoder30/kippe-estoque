import sqlite3
from typing import Optional
from src.domain.operator import Operator

class SQLiteOperatorRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS operators (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    pin_hash TEXT NOT NULL,
                    role TEXT NOT NULL
                )
            ''')
            conn.commit()

    def save(self, operator: Operator) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO operators (id, name, pin_hash, role) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET 
                    name=excluded.name, 
                    pin_hash=excluded.pin_hash,
                    role=excluded.role
            ''', (operator.id, operator.name, operator.pin_hash, operator.role))
            conn.commit()

    def get_by_id(self, operator_id: str) -> Optional[Operator]:
        with self._get_connection() as conn:
            row = conn.execute('SELECT * FROM operators WHERE id = ?', (operator_id,)).fetchone()
            if row:
                return Operator(
                    id=row['id'], 
                    name=row['name'], 
                    pin_hash=row['pin_hash'], 
                    role=row['role']
                )
            return None
