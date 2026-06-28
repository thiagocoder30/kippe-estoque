import os
import sys
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor
def patch_repository(content: str) -> str:
    # Injeta a coluna no SQLite com segurança dict(row) para evitar o erro AttributeError da sqlite3.Row
    add_col = '''            cursor = conn.execute("PRAGMA table_info(products)")
            columns = [info['name'] for info in cursor.fetchall()]
            if 'allow_negative_stock' not in columns:
                conn.execute("ALTER TABLE products ADD COLUMN allow_negative_stock INTEGER NOT NULL DEFAULT 0")'''
    if "allow_negative_stock" not in content:
        content = content.replace("conn.commit()", add_col + "\n            conn.commit()", 1)
        
        content = content.replace(
            "category_id, reserved_quantity)",
            "category_id, reserved_quantity, allow_negative_stock)"
        )
        content = content.replace(
            "category_id=excluded.category_id, reserved_quantity=excluded.reserved_quantity",
            "category_id=excluded.category_id, reserved_quantity=excluded.reserved_quantity, allow_negative_stock=excluded.allow_negative_stock"
        )
        content = content.replace(
            "product.category_id, product.reserved_quantity))",
            "product.category_id, product.reserved_quantity, int(product.allow_negative_stock)))"
        )
        
        # O uso de dict() garante que não acionaremos o erro da sqlite3.Row não suportar .get()
        content = content.replace(
            "status=prod_row['status'], category_id=prod_row['category_id']",
            "status=prod_row['status'], category_id=prod_row['category_id'], allow_negative_stock=bool(dict(prod_row).get('allow_negative_stock', 0))"
        )
        content = content.replace(
            "status=row['status'], category_id=row['category_id']",
            "status=row['status'], category_id=row['category_id'], allow_negative_stock=bool(dict(row).get('allow_negative_stock', 0))"
        )
    return content
try:
    with SafeRefactor("src/interfaces/sqlite_repository.py") as sr:
        sr.apply(patch_repository)
except Exception as e:
    sys.exit(1)
