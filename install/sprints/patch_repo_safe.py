from install.lib.refactor_engine import SafeRefactor

def patch(content: str) -> str:
    if "cost_per_unit" not in content:
        content = content.replace(
            "batch.location_id, batch.warehouse_id)",
            "batch.location_id, batch.warehouse_id, getattr(batch, 'cost_per_unit', 0.0))"
        )
    return content

with SafeRefactor("src/interfaces/sqlite_repository.py") as sr:
    sr.apply(patch)
