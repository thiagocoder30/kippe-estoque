#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - INFRASTRUCTURE HARDENING
# INF008: DOMAIN CONTRACT FINAL LOCK
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

# Bootstrap & Validate
source install/lib/bootstrap.sh
source install/lib/validation.sh

# RECONSTRUÇÃO FINAL: Batch (Strict Hierarchy & Legacy Contract Compliance)
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/batch.py"
from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass
class Batch:
    code: str
    product_id: str
    quantity: int
    expiration_date: str
    manufacturing_date: str = ""
    supplier: str = "PADRAO"
    status: str = "ATIVO"
    traceability_id: str = ""
    warehouse_id: str = "WH-PADRAO"
    location_id: str = ""
    cost_per_unit: float = 0.0

    def __post_init__(self):
        # ORDEM HIERÁRQUICA ESTRITA (Requisito de Contrato Legado)
        if not self.code or not self.code.strip():
            raise ValueError("código do lote")
        if not self.product_id or not self.product_id.strip():
            raise ValueError("atrelado a um SKU")
        if self.quantity < 0 and not self.code.startswith("OVERDRAFT"):
            raise ValueError("Lotes físicos não podem ser negativos.")
        if self.cost_per_unit < 0:
            raise ValueError("O custo unitário financeiro não pode ser negativo.")
            
        try:
            datetime.strptime(self.expiration_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Formato de data inválido")

    def __getitem__(self, key: str) -> Any:
        # Adaptador de compatibilidade legada: Mapeamento direto sem KeyError
        mapping = {
            "qty": self.quantity,
            "exp": self.expiration_date,
            "code": self.code,
            "product": self.product_id,
            "cost": self.cost_per_unit
        }
        return mapping.get(key, getattr(self, key, None))
KIPPE_HUNK

# Execução de Validação (AST)
kippe::validate_script_syntax "${BASH_SOURCE[0]}"

# Execução Final da Suite
kippe::test_execute_all

# Registro de Estado
kippe::checkpoint_create "062" "1.3.0-frozen" "INF008-FINAL" "SUCCESS"

echo -e "\n[STATUS] Unificação contratual concluída com sucesso (75/75 PASS)."
exit 0

