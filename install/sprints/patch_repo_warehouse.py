import os
import sys
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor

def inject_repo_warehouse_schema(content: str) -> str:
    # 1. Cria a tabela institucional de armazéns e insere a coluna na tabela de lotes
    tables = """
            conn.execute('''
                CREATE TABLE IF NOT EXISTS warehouses (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, address TEXT, is_active INTEGER DEFAULT 1
                )
            ''')
            
            cursor = conn.execute("PRAGMA table_info(batches)")
            columns = [info['name'] for info in cursor.fetchall()]
            if 'warehouse_id' not in columns:
                conn.execute("ALTER TABLE batches ADD COLUMN warehouse_id TEXT DEFAULT 'WH-PADRAO'")
"""
    if "CREATE TABLE IF NOT EXISTS warehouses" not in content:
        content = content.replace(
            "CREATE TABLE IF NOT EXISTS locations (",
            tables + "\n            CREATE TABLE IF NOT EXISTS locations ("
        )
        
    # 2. Atualiza a injeção de parâmetros nos métodos de salvamento e carga
    content = content.replace(
        "traceability_id, location_id) \n                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        "traceability_id, location_id, warehouse_id) \n                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    content = content.replace(
        "batch.traceability_id, batch.location_id))",
        "batch.traceability_id, batch.location_id, batch.warehouse_id))"
    )
    content = content.replace(
        "location_id=row.get('location_id', '')",
        "location_id=row.get('location_id', ''), warehouse_id=row.get('warehouse_id', 'WH-PADRAO')"
    )
    content = content.replace(
        "location_id=b.get('location_id', '')",
        "location_id=b.get('location_id', ''), warehouse_id=b.get('warehouse_id', 'WH-PADRAO')"
    )
    return content

try:
    with SafeRefactor("src/interfaces/sqlite_repository.py") as sr:
        sr.apply(inject_repo_warehouse_schema)
except Exception as e:
    sys.exit(1)
