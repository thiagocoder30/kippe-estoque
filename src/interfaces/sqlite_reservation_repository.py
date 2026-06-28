import sqlite3
from typing import List
from src.domain.reservation import Reservation
class SQLiteReservationRepository:
    """
    Segregação de Responsabilidade (SRP):
    Isola a persistência do ciclo de vida das alocações lógicas.
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
                CREATE TABLE IF NOT EXISTS reservations (
                    id TEXT PRIMARY KEY, product_id TEXT NOT NULL, amount INTEGER NOT NULL,
                    operator_id TEXT NOT NULL, status TEXT NOT NULL, created_at DATETIME NOT NULL,
                    expires_at DATETIME NOT NULL
                )
            ''')
            # Migração Transparente para TTL
            cursor = conn.execute("PRAGMA table_info(reservations)")
            columns = [info['name'] for info in cursor.fetchall()]
            if 'expires_at' not in columns:
                conn.execute("ALTER TABLE reservations ADD COLUMN expires_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP")
            conn.commit()
    def save(self, reservation: Reservation) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO reservations (id, product_id, amount, operator_id, status, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET status=excluded.status
            ''', (reservation.id, reservation.product_id, reservation.amount, reservation.operator_id, 
                  reservation.status, reservation.created_at, reservation.expires_at))
            conn.commit()
    def get_pending_by_product(self, product_id: str) -> List[Reservation]:
        with self._get_connection() as conn:
            rows = conn.execute('SELECT * FROM reservations WHERE product_id = ? AND status = "PENDING"', (product_id,)).fetchall()
            return [Reservation(
                id=r['id'], product_id=r['product_id'], amount=r['amount'], operator_id=r['operator_id'],
                status=r['status'], created_at=r['created_at'], expires_at=r['expires_at']
            ) for r in rows]
