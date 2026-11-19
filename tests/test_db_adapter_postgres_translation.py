from src.infrastructure.db_adapter import (
    HybridRow,
    PostgresConnectionAdapter,
    translate_sql_to_postgres,
)


def test_hybrid_row_supports_dict_keys_and_tuple_indices():
    row = HybridRow({"id": "SKU-1", "name": "ARROZ 5KG", "quantity": 40})
    assert row["id"] == "SKU-1"
    assert row["quantity"] == 40
    assert row[0] == "SKU-1"
    assert row[2] == 40


def test_postgres_sql_translation_rules():
    # Placeholders fora de literais
    sql1, meta1 = translate_sql_to_postgres("SELECT * FROM products WHERE ean = ? AND name != '?'")
    assert sql1 == "SELECT * FROM products WHERE ean = %s AND name != '?'"
    assert meta1 == {}

    # DDL AUTOINCREMENT + DATETIME
    sql2, _ = translate_sql_to_postgres(
        "CREATE TABLE transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)"
    )
    assert "SERIAL PRIMARY KEY" in sql2
    assert "TIMESTAMP DEFAULT CURRENT_TIMESTAMP" in sql2

    # INSERT OR IGNORE
    sql3, _ = translate_sql_to_postgres("INSERT OR IGNORE INTO categories (id, name) VALUES (?, ?)")
    assert sql3 == "INSERT INTO categories (id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING"

    # PRAGMA table_info
    sql4, meta4 = translate_sql_to_postgres("PRAGMA table_info(products)")
    assert meta4["pragma_table_info"] == "products"
    assert "information_schema.columns" in sql4

    # RETURNING id para lastrowid
    sql5, meta5 = translate_sql_to_postgres(
        "INSERT INTO receiving_pending_queue (supplier, invoice_number) VALUES (?, ?)"
    )
    assert sql5.endswith("RETURNING id")
    assert meta5["returning_id"] is True


def test_postgres_cursor_adapter_captures_lastrowid():
    class FakeRawCursor:
        rowcount = 1
        last_query = None

        def execute(self, sql, params=None):
            self.last_query = (sql, params)

        def fetchone(self):
            return {"id": 42}

        def fetchall(self):
            return [{"id": 42}]

    class FakeRawConn:
        def cursor(self):
            return FakeRawCursor()

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    conn = PostgresConnectionAdapter(FakeRawConn())
    cur = conn.execute(
        "INSERT INTO operational_audit_events (event_type, product_id, operator_id) VALUES (?, ?, ?)",
        ("RECEIVE", "SKU-1", "ADM-01"),
    )
    assert cur.lastrowid == 42
