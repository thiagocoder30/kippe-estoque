import os
import sys
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor

def inject_warehouse_field(content: str) -> str:
    # Adiciona a propriedade de armazém na raiz do Lote para alta performance de roteamento
    if "warehouse_id: str = \"WH-PADRAO\"" not in content:
        content = content.replace(
            "location_id: str = \"\"  # Endereçamento físico (INV007)",
            "location_id: str = \"\"  # Endereçamento físico (INV007)\n    warehouse_id: str = \"WH-PADRAO\""
        )
    # Garante suporte a dicionário polimórfico para os testes legados
    if "if item == 'location_id': return self.location_id" in content and "warehouse_id" not in content:
        content = content.replace(
            "if item == 'location_id': return self.location_id",
            "if item == 'location_id': return self.location_id\n        if item == 'warehouse_id': return self.warehouse_id"
        )
    return content

try:
    with SafeRefactor("src/domain/batch.py") as sr:
        sr.apply(inject_warehouse_field)
except Exception as e:
    sys.exit(1)
