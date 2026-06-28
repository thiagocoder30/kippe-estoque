import os
import sys
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor

def inject_warehouse_methods(content: str) -> str:
    methods = """
    def get_stock_by_warehouse(self, warehouse_id: str) -> int:
        \"\"\"Consolida matematicamente o saldo físico do SKU em uma planta específica.\"\"\"
        return sum(b.quantity for b in self.batches.values() if b.warehouse_id == warehouse_id)

    def get_available_stock_by_warehouse(self, warehouse_id: str) -> int:
        \"\"\"Retorna o saldo livre para comercialização por planta, deduzindo travas lógicas.\"\"\"
        # Como as reservas atuais são globais, a disponibilidade local é proporcional ao estoque físico local
        total_physical = self.quantity
        if total_physical == 0: return 0
        local_physical = self.get_stock_by_warehouse(warehouse_id)
        local_reserved = int((self.reserved_quantity * local_physical) / total_physical)
        return local_physical - local_reserved
"""
    if "def get_stock_by_warehouse" not in content:
        # Encontra o final da classe ou um método conhecido para injetar as novas capacidades
        content = content.replace(
            "def can_be_removed(self) -> bool:",
            methods + "\n    def can_be_removed(self) -> bool:"
        )
    return content

try:
    with SafeRefactor("src/domain/product.py") as sr:
        sr.apply(inject_warehouse_methods)
except Exception as e:
    sys.exit(1)
