#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# INFRASTRUCTURE HARDENING
# SPRINT INF008: DOMAIN CONTRACT UNIFICATION LAYER
# ============================================================
set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"
# 1. Bootstrap
source install/lib/bootstrap.sh
source install/lib/testing.sh
source install/lib/validation.sh
kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR
TOTAL_STEPS=4
kippe::banner_program "INF" "INF008" "Domain Contract Unification Layer"
kippe::step 1 ${TOTAL_STEPS} "Deploying Canonical Domain Model (Strict Batch + Legacy Adapter)..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/batch.py"
from dataclasses import dataclass
from datetime import datetime
from typing import Any
@dataclass
class Batch:
    """
    Entidade Canônica: Batch (Lote)
    Contrato rígido de domínio. Implementa Validação Estrita (Strict Validation)
    e um Adaptador de Retrocompatibilidade (Legacy Adapter) livre de exceções.
    """
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
        # Validação Canônica Centralizada (Sem negociação)
        if not self.code or not self.code.strip():
            raise ValueError("O código do lote é obrigatório e não pode ser vazio.")
        if not self.product_id or not self.product_id.strip():
            raise ValueError("O product_id é obrigatório para vínculo do lote.")
        if self.quantity < 0 and not self.code.startswith("OVERDRAFT"):
            raise ValueError("Violação de Invariante: Lotes físicos não podem ser negativos.")
        if self.cost_per_unit < 0:
            raise ValueError("O custo unitário financeiro não pode ser negativo.")
            
        try:
            datetime.strptime(self.expiration_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Formato de data inválido. Utilize o padrão ISO (YYYY-MM-DD).")
    def is_expired(self) -> bool:
        try:
            exp = datetime.strptime(self.expiration_date, "%Y-%m-%d")
            return datetime.now() > exp
        except ValueError:
            return False
    # Legacy Compatibility Adapter (Safe Dictionary Access)
    def __getitem__(self, key: str) -> Any:
        mapping = {
            "qty": self.quantity,
            "exp": self.expiration_date,
            "code": self.code,
            "product": self.product_id,
            "cost": self.cost_per_unit
        }
        
        if key in mapping:
            return mapping[key]
            
        if hasattr(self, key):
            return getattr(self, key)
            
        # O retorno estrito de None elimina o KeyError em infraestruturas antigas
        return None
KIPPE_HUNK
kippe::step 2 ${TOTAL_STEPS} "Applying Repository Contract Lock (Strict Persistence Mapping)..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/sprints/hotfix_repo_lock.py"
import os
import sys
import re
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor
def patch_repo_strict_mapping(content: str) -> str:
    # Assegura que o mapeamento SQLite -> Domain (Leitura) é explícito e tipado
    pattern_read = re.compile(r'batches_dict\[b_dict\[\'batch_code\'\]\] = Batch\(.*?cost_per_unit=.*?\)', re.DOTALL)
    strict_read = '''batches_dict[b_dict['batch_code']] = Batch(
                        code=str(b_dict['batch_code']), 
                        product_id=str(b_dict['product_id']), 
                        quantity=int(b_dict['quantity']),
                        expiration_date=str(b_dict['expiration_date']), 
                        warehouse_id=str(b_dict.get('warehouse_id', 'WH-PADRAO')),
                        location_id=str(b_dict.get('location_id', '')), 
                        manufacturing_date=str(b_dict.get('manufacturing_date', '')),
                        supplier=str(b_dict.get('supplier', 'PADRAO')), 
                        status=str(b_dict.get('status', 'ATIVO')), 
                        traceability_id=str(b_dict.get('traceability_id', '')),
                        cost_per_unit=float(b_dict.get('cost_per_unit', 0.0))
                    )'''
    content = pattern_read.sub(strict_read, content)
    
    # Assegura o mapeamento em get_by_id (Duplicidade histórica do repo)
    pattern_read_id = re.compile(r'batches_dict\[r_dict\[\'batch_code\'\]\] = Batch\(.*?cost_per_unit=.*?\)', re.DOTALL)
    strict_read_id = '''batches_dict[r_dict['batch_code']] = Batch(
                    code=str(r_dict['batch_code']), 
                    product_id=str(r_dict['product_id']), 
                    quantity=int(r_dict['quantity']),
                    expiration_date=str(r_dict['expiration_date']), 
                    warehouse_id=str(r_dict.get('warehouse_id', 'WH-PADRAO')),
                    location_id=str(r_dict.get('location_id', '')), 
                    manufacturing_date=str(r_dict.get('manufacturing_date', '')),
                    supplier=str(r_dict.get('supplier', 'PADRAO')), 
                    status=str(r_dict.get('status', 'ATIVO')), 
                    traceability_id=str(r_dict.get('traceability_id', '')),
                    cost_per_unit=float(r_dict.get('cost_per_unit', 0.0))
                )'''
    content = pattern_read_id.sub(strict_read_id, content)
    # Assegura que o mapeamento Domain -> SQLite (Escrita) é explícito e tipado
    pattern_write = re.compile(r'VALUES \(\?, \?, \?, \?, \?, \?, \?, \?, \?, \?, \?\).*?\)', re.DOTALL)
    strict_write = '''VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(product.id), str(batch.code), str(batch.expiration_date), int(batch.quantity), 
                    str(batch.manufacturing_date), str(batch.supplier), str(batch.status), 
                    str(batch.traceability_id), str(batch.location_id), str(batch.warehouse_id), 
                    float(batch.cost_per_unit)
                ))'''
    
    if "float(batch.cost_per_unit)" not in content:
        content = pattern_write.sub(strict_write, content)
    return content
try:
    with SafeRefactor("src/interfaces/sqlite_repository.py") as sr:
        sr.apply(patch_repo_strict_mapping)
except Exception as e:
    sys.exit(1)
KIPPE_HUNK
python3 "${KIPPE_ROOT}/install/sprints/hotfix_repo_lock.py"
# 3. Semantic Validator & 4. AST Compile
kippe::step 3 ${TOTAL_STEPS} "Verifying Canonical Integrity via Semantic and AST Gates..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
# 5. Regression Suite
kippe::step 4 ${TOTAL_STEPS} "Executing Core Regression Suite (Attesting Unification)..."
kippe::test_execute_all
# 6. Architecture Scorecard
cat << "SCORECARD" > "${KIPPE_ROOT}/docs/checkpoints/ARCHITECTURE_SCORECARD-INF008.md"
# Architecture Scorecard - Kippe Platform
### Sprint: INF008 - Domain Contract Unification Layer

| Critério | Status | Detalhes |
| :--- | :--- | :--- |
| **Testes passando** | ✅ | GREEN. Contratos estritos validados. |
| **Canonical Domain** | ✅ | Entidade \`Batch\` completamente selada. |
| **Legacy Adapter** | ✅ | Dict-behavior reimplementado (\`__getitem__\`) com fallback nulo (\`No KeyError\`). |
| **Repository Lock** | ✅ | Escrita e leitura explicitamente tipadas e convertidas antes do SQLite. |

SCORECARD
# 7. Checkpoint & 8. Manifest
kippe::checkpoint_create "061" "1.3.0-frozen" "INF008" "SUCCESS"
kippe::manifest_create "INF008" "INF" "1.3.0-frozen" "SUCCESS" "INV019"
# Limpeza de artefatos
rm -f "${KIPPE_ROOT}"/install/sprints/hotfix_*.py
rm -f data/test_*.db data/test_*.log data/test_*.db-journal 2>/dev/null || true
# 9 a 12. Sincronização Compulsória do Estado Permanente
kippe::governance_sync \
    "C" \
    "Inventory" \
    "3" \
    "Institucional" \
    "C.5" \
    "Institutional Ready" \
    "INF008 (Domain Unification Layer)" \
    "INV019 — Inventory Valuation (Read Model)" \
    "19/20 Sprints" \
    "STABLE"
exit 0
