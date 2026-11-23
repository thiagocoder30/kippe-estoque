import os
import re
import sqlite3
from typing import Any, Iterable, Optional


SERIAL_ID_TABLES = {
    "operational_audit_events",
    "transactions",
    "receiving_pending_queue",
    "product_registration_requests",
    "institutional_audit_log",
    "receiving_divergences",
    "conference_audit_log",
}


class HybridRow(dict):
    """Compatível com dict ('row[\"col\"]') e sqlite3.Row ('row[0]')."""

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def is_postgres_enabled() -> bool:
    if os.getenv("FORCE_POSTGRES_ADAPTER") == "1":
        return True
    if os.getenv("ENV", "").strip().lower() == "testing" or os.getenv("PYTEST_CURRENT_TEST"):
        return False
    db_url = os.getenv("DATABASE_URL", "").strip()
    return db_url.startswith("postgres://") or db_url.startswith("postgresql://")


def _replace_outside_quotes(sql: str, replacer) -> str:
    parts = re.split(r"('(?:''|[^'])*')", sql)
    for idx in range(0, len(parts), 2):
        parts[idx] = replacer(parts[idx])
    return "".join(parts)



def _glob_pattern_to_pg_regex(match: re.Match) -> str:
    pat = match.group(1)
    out = ["^"]
    i = 0
    while i < len(pat):
        ch = pat[i]
        if ch == "*":
            out.append(".*")
        elif ch == "?":
            out.append(".")
        elif ch == "[":
            j = pat.find("]", i + 1)
            if j != -1:
                bracket = pat[i : j + 1]
                if bracket.startswith("[!"):
                    bracket = "[^" + bracket[2:]
                out.append(bracket)
                i = j
            else:
                out.append(r"\[")
        elif ch in r"\.$^+{}()|":
            out.append("\\" + ch)
        else:
            out.append(ch)
        i += 1
    out.append("$")
    return f"~ '{''.join(out)}'"


def translate_sql_to_postgres(sql: str) -> tuple[str, dict]:
    raw = sql.strip()
    meta: dict[str, Any] = {}

    # 0. Transacoes SQLite (BEGIN IMMEDIATE/EXCLUSIVE/DEFERRED -> BEGIN)
    if re.match(r"^BEGIN\s+(?:IMMEDIATE|EXCLUSIVE|DEFERRED)\s*;?$", raw, re.IGNORECASE):
        return "BEGIN", meta

    # 1. PRAGMA table_info(tabela)
    m_pragma = re.match(r"^PRAGMA\s+table_info\(\s*([a-zA-Z0-9_]+)\s*\)\s*;?$", raw, re.IGNORECASE)
    if m_pragma:
        tbl = m_pragma.group(1)
        meta["pragma_table_info"] = tbl
        return (
            "SELECT ordinal_position - 1 AS cid, column_name AS name, data_type AS type, "
            "CASE WHEN is_nullable = 'NO' THEN 1 ELSE 0 END AS notnull, "
            "column_default AS dflt_value, 0 AS pk "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s "
            "ORDER BY ordinal_position",
            meta,
        )

    # 2. Introspecção sqlite_master
    if re.search(r"FROM\s+sqlite_master\b", raw, re.IGNORECASE):
        return (
            "SELECT table_name AS name FROM information_schema.tables WHERE table_schema = 'public'",
            meta,
        )

    # 3. DDL: AUTOINCREMENT, DATETIME, BLOB
    translated = _replace_outside_quotes(
        raw,
        lambda seg: re.sub(
            r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b",
            "SERIAL PRIMARY KEY",
            seg,
            flags=re.IGNORECASE,
        ),
    )
    translated = _replace_outside_quotes(
        translated,
        lambda seg: re.sub(r"\bDATETIME\b", "TIMESTAMP", seg, flags=re.IGNORECASE),
    )
    translated = _replace_outside_quotes(
        translated,
        lambda seg: re.sub(r"\bBLOB\b", "BYTEA", seg, flags=re.IGNORECASE),
    )

    # 4. INSERT OR IGNORE -> ON CONFLICT DO NOTHING
    if re.match(r"^INSERT\s+OR\s+IGNORE\s+INTO\b", translated, re.IGNORECASE):
        translated = re.sub(r"^INSERT\s+OR\s+IGNORE\s+INTO\b", "INSERT INTO", translated, count=1, flags=re.IGNORECASE)
        translated = translated.rstrip(";") + " ON CONFLICT DO NOTHING"

    # 5. INSERT OR REPLACE -> ON CONFLICT (sku) DO UPDATE
    m_rep_cat = re.match(r"^INSERT\s+OR\s+REPLACE\s+INTO\s+catalog\b", translated, re.IGNORECASE)
    if m_rep_cat:
        translated = re.sub(
            r"^INSERT\s+OR\s+REPLACE\s+INTO\s+catalog\b",
            "INSERT INTO catalog",
            translated,
            count=1,
            flags=re.IGNORECASE,
        )
        translated = (
            translated.rstrip(";")
            + " ON CONFLICT (sku) DO UPDATE SET description = EXCLUDED.description, "
            "brand = EXCLUDED.brand, category = EXCLUDED.category, photo = EXCLUDED.photo"
        )

    m_rep_led = re.match(r"^INSERT\s+OR\s+REPLACE\s+INTO\s+ledger\b", translated, re.IGNORECASE)
    if m_rep_led:
        translated = re.sub(
            r"^INSERT\s+OR\s+REPLACE\s+INTO\s+ledger\b",
            "INSERT INTO ledger",
            translated,
            count=1,
            flags=re.IGNORECASE,
        )
        translated = translated.rstrip(";") + " ON CONFLICT (sku) DO UPDATE SET data = EXCLUDED.data"

    # 5b. GLOB -> POSIX regex (~) (GLOB_TRANSLATED_IN_FUNC)
    translated = re.sub(r"\bGLOB\s+'([^']*)'", _glob_pattern_to_pg_regex, translated, flags=re.IGNORECASE)

    # 6. Placeholders ? -> %s fora de literais
    translated = _replace_outside_quotes(translated, lambda seg: seg.replace("?", "%s"))

    # 7. Captura de lastrowid em tabelas com SERIAL PRIMARY KEY
    m_ins = re.match(r"^INSERT\s+INTO\s+([a-zA-Z0-9_]+)\b", translated, re.IGNORECASE)
    if m_ins and "RETURNING" not in translated.upper():
        tbl_name = m_ins.group(1).lower()
        if tbl_name in SERIAL_ID_TABLES:
            translated = translated.rstrip(";") + " RETURNING id"
            meta["returning_id"] = True

    return translated, meta


class PostgresCursorAdapter:
    def __init__(self, raw_cursor: Any):
        self._cur = raw_cursor
        self.lastrowid: Optional[int] = None

    @property
    def rowcount(self) -> int:
        return self._cur.rowcount

    def execute(self, sql: str, params: Optional[Iterable[Any]] = None) -> "PostgresCursorAdapter":
        pg_sql, meta = translate_sql_to_postgres(sql)
        if "pragma_table_info" in meta:
            self._cur.execute(pg_sql, (meta["pragma_table_info"],))
            return self

        if params is not None:
            self._cur.execute(pg_sql, tuple(params))
        else:
            self._cur.execute(pg_sql)

        if meta.get("returning_id"):
            row = self._cur.fetchone()
            if row is not None:
                self.lastrowid = int(row["id"] if isinstance(row, dict) else row[0])
        return self

        if params is not None:
            self._cur.execute(pg_sql, tuple(params))
        else:
            pg_sql = re.sub(r"\bGLOB\s+'([^']*)'", _glob_pattern_to_pg_regex, pg_sql, flags=re.IGNORECASE)
        self._cur.execute(pg_sql)

        if meta.get("returning_id"):
            row = self._cur.fetchone()
            if row is not None:
                self.lastrowid = int(row["id"] if isinstance(row, dict) else row[0])
        return self

    def executemany(self, sql: str, seq_of_params: Iterable[Iterable[Any]]) -> "PostgresCursorAdapter":
        pg_sql, _ = translate_sql_to_postgres(sql)
        self._cur.executemany(pg_sql, [tuple(p) for p in seq_of_params])
        return self

    def fetchone(self) -> Optional[HybridRow]:
        row = self._cur.fetchone()
        if row is None:
            return None
        return HybridRow(row)

    def fetchall(self) -> list[HybridRow]:
        return [HybridRow(r) for r in self._cur.fetchall()]

    def __iter__(self):
        for r in self._cur:
            yield HybridRow(r)


class PostgresConnectionAdapter:
    def __init__(self, raw_conn: Any):
        self._conn = raw_conn
        self.row_factory: Any = HybridRow

    def cursor(self) -> PostgresCursorAdapter:
        return PostgresCursorAdapter(self._conn.cursor())

    def execute(self, sql: str, params: Optional[Iterable[Any]] = None) -> PostgresCursorAdapter:
        cur = self.cursor()
        return cur.execute(sql, params)

    def executemany(self, sql: str, seq_of_params: Iterable[Iterable[Any]]) -> PostgresCursorAdapter:
        cur = self.cursor()
        return cur.executemany(sql, seq_of_params)

    def executescript(self, sql_script: str) -> None:
        statements = [s.strip() for s in sql_script.split(";") if s.strip()]
        for stmt in statements:
            self.execute(stmt)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "PostgresConnectionAdapter":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()


def connect_db(db_path: str = "data/estoque_producao.db") -> Any:
    if is_postgres_enabled():
        import psycopg
        from psycopg.rows import dict_row

        db_url = os.getenv("DATABASE_URL", "").strip()
        raw_conn = psycopg.connect(
            db_url,
            row_factory=dict_row,
            prepare_threshold=None,
        )
        return PostgresConnectionAdapter(raw_conn)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn
