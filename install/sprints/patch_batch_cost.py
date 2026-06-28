import os
import sys
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor
def patch_batch_with_cost(content: str) -> str:
    if "cost_per_unit: float" not in content:
        content = content.replace(
            "location_id: str = ''",
            "location_id: str = ''\n    cost_per_unit: float = 0.0"
        )
    return content
try:
    with SafeRefactor("src/domain/batch.py") as sr:
        sr.apply(patch_batch_with_cost)
except Exception as e:
    print(f"Abortando mutação: {e}")
    sys.exit(1)
