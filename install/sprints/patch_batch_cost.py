import os
import sys
import re
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor
def patch_batch_with_cost(content: str) -> str:
    # Adiciona o atributo financeiro sem quebrar construtores existentes (default 0.0)
    if "cost_per_unit: float" not in content:
        content = content.replace(
            "location_id: str = ''",
            "location_id: str = ''\n    cost_per_unit: float = 0.0"
        )
    return content
def patch_repo_with_cost(content: str) -> str:
    # Garante que o SQLite suporte a leitura/escrita do custo retroativamente
    add_col = '''            cursor = conn.execute("PRAGMA table_info(batches)")
            columns = [info['name'] for info in cursor.fetchall()]
            if 'cost_per_unit' not in columns:
                conn.execute("ALTER TABLE batches ADD COLUMN cost_per_unit REAL NOT NULL DEFAULT 0.0")'''
                
    if "cost_per_unit" not in content:
        content = content.replace(
            "if 'allow_negative_stock' not in columns:",
            add_col + "\n            if 'allow_negative_stock' not in columns:"
        )
        content = content.replace(
            "location_id, warehouse_id)",
            "location_id, warehouse_id, cost_per_unit)"
        )
        content = content.replace(
            "batch.location_id, batch.warehouse_id))",
            "batch.location_id, batch.warehouse_id, float(batch.cost_per_unit)))"
        )
        content = content.replace(
            "status=row_dict['status'], traceability_id=row_dict['traceability_id']",
            "status=row_dict['status'], traceability_id=row_dict['traceability_id'], cost_per_unit=float(row_dict.get('cost_per_unit', 0.0))"
        )
        content = content.replace(
            "status=b_dict['status'], traceability_id=b_dict['traceability_id']",
            "status=b_dict['status'], traceability_id=b_dict['traceability_id'], cost_per_unit=float(b_dict.get('cost_per_unit', 0.0))"
        )
    return content
try:
    with SafeRefactor("src/domain/batch.py") as sr:
        sr.apply(patch_batch_with_cost)
    with SafeRefactor("src/interfaces/sqlite_repository.py") as sr:
        sr.apply(patch_repo_with_cost)
except Exception as e:
    sys.exit(1)
