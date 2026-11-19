#!/usr/bin/env python3
"""
Migra 100% dos dados locais (data/estoque_producao.db + kippe.db)
para o PostgreSQL do Supabase sem perda de registros ou IDs.

Uso:
  DATABASE_URL="postgresql://..." python3 scripts/migrate_to_supabase.py
"""
import os
import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))


MAIN_TABLES_ORDER = [
    "categories",
    "warehouses",
    "locations",
    "products",
    "batches",
    "operators",
    "sku_sequences",
    "transactions",
    "operational_audit_events",
    "document_attachments",
    "operational_audit_event_attachments",
    "receiving_operations",
    "reservations",
    "inventory_ledger",
    "inventory_snapshots",
]

AUX_TABLES_ORDER = [
    "catalog",
    "ledger",
    "sku_aliases",
    "sku_pack_defaults",
    "receiving_pending_queue",
    "product_registration_requests",
    "institutional_audit_log",
    "receiving_divergences",
    "conference_audit_log",
]

SERIAL_TABLES = [
    "operational_audit_events",
    "transactions",
    "receiving_pending_queue",
    "product_registration_requests",
    "institutional_audit_log",
    "receiving_divergences",
    "conference_audit_log",
]


def _read_sqlite_table(sqlite_path: Path, table_name: str) -> tuple[list[str], list[tuple]]:
    if not sqlite_path.exists():
        return [], []
    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    try:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
        if not exists:
            return [], []
        rows = conn.execute(f'SELECT * FROM "{table_name}"').fetchall()
        if not rows:
            return [], []
        cols = list(rows[0].keys())
        data = [tuple(r[c] for c in cols) for r in rows]
        return cols, data
    finally:
        conn.close()


def migrate() -> None:
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not (db_url.startswith("postgres://") or db_url.startswith("postgresql://")):
        print("❌ Defina DATABASE_URL com a URI PostgreSQL do Supabase antes de rodar.")
        print('   Exemplo: export DATABASE_URL="postgresql://postgres.[REF]:[SENHA]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"')
        sys.exit(1)

    os.environ["ENV"] = "production"
    os.environ["FORCE_POSTGRES_ADAPTER"] = "1"

    import app as gateway_app
    from src.infrastructure.db_adapter import connect_db

    print("1/4 · Inicializando esquema PostgreSQL no Supabase...")
    for attr_name in dir(gateway_app.container):
        repo_obj = getattr(gateway_app.container, attr_name, None)
        if hasattr(repo_obj, "_init_db") and callable(repo_obj._init_db):
            repo_obj._init_db()

    conn_aux_init = gateway_app._get_kippe_db()
    conn_aux_init.close()

    main_sqlite = ROOT_DIR / "data" / "estoque_producao.db"
    aux_sqlite = ROOT_DIR / "kippe.db"

    pg_conn = connect_db()
    total_migrated = 0

    try:
        print("\n2/4 · Migrando tabelas principais (data/estoque_producao.db)...")
        for tbl in MAIN_TABLES_ORDER:
            cols, rows = _read_sqlite_table(main_sqlite, tbl)
            if not rows:
                print(f"   • {tbl}: 0 registros (vazia)")
                continue
            col_list = ", ".join(f'"{c}"' for c in cols)
            placeholders = ", ".join(["%s"] * len(cols))
            sql = f'INSERT INTO "{tbl}" ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
            raw_cur = pg_conn._conn.cursor()
            raw_cur.executemany(sql, rows)
            pg_conn.commit()
            total_migrated += len(rows)
            print(f"   ✅ {tbl}: {len(rows)} registros sincronizados")

        print("\n3/4 · Migrando tabelas auxiliares e auditoria (kippe.db)...")
        for tbl in AUX_TABLES_ORDER:
            cols, rows = _read_sqlite_table(aux_sqlite, tbl)
            if not rows:
                print(f"   • {tbl}: 0 registros (vazia)")
                continue
            col_list = ", ".join(f'"{c}"' for c in cols)
            placeholders = ", ".join(["%s"] * len(cols))
            sql = f'INSERT INTO "{tbl}" ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
            raw_cur = pg_conn._conn.cursor()
            raw_cur.executemany(sql, rows)
            pg_conn.commit()
            total_migrated += len(rows)
            print(f"   ✅ {tbl}: {len(rows)} registros sincronizados")

        print("\n4/4 · Sincronizando sequências SERIAL (AUTO_INCREMENT) no PostgreSQL...")
        raw_cur = pg_conn._conn.cursor()
        for tbl in SERIAL_TABLES:
            raw_cur.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{tbl}', 'id'),
                    COALESCE((SELECT MAX(id) FROM "{tbl}"), 1),
                    (SELECT COUNT(*) > 0 FROM "{tbl}")
                )
                """
            )
        pg_conn.commit()
    finally:
        pg_conn.close()

    print(f"\n🏆 MIGRAÇÃO CONCLUÍDA COM SUCESSO: {total_migrated} registros transferidos para o Supabase!")


if __name__ == "__main__":
    migrate()
