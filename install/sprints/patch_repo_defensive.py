import os
import sys
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor
def make_repo_defensive(content: str) -> str:
    # Substitui acessos diretos inseguros por getattr defensivo
    old_insert = "batch.location_id, batch.warehouse_id, float(batch.cost_per_unit)))"
    new_insert = "batch.location_id, batch.warehouse_id, float(getattr(batch, 'cost_per_unit', 0.0))))"
    
    if old_insert in content:
        return content.replace(old_insert, new_insert)
    return content
try:
    with SafeRefactor("src/interfaces/sqlite_repository.py") as sr:
        sr.apply(make_repo_defensive)
except Exception as e:
    print(f"Abortando mutação defensiva: {e}")
    sys.exit(1)
