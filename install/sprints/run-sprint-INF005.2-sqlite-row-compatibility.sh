#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# INFRASTRUCTURE HARDENING
# SPRINT INF005.2: SQLITE ROW COMPATIBILITY LAYER
# ============================================================

set -Eeuo pipefail

export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

source install/lib/bootstrap.sh
source install/lib/testing.sh
source install/lib/validation.sh

kippe::init
kippe::init_environment

trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=5

kippe::banner_program \
    "INF" \
    "INF005.2" \
    "SQLite Row Compatibility Layer & Semantic Supercharge"

kippe::step 1 ${TOTAL_STEPS} "Applying Structural Fix: SQLite Row Dictionary Compatibility..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/sprints/hotfix_sqlite_row.py"
import os
import sys
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor

def patch_row_get_incompatibility(content: str) -> str:
    # 1. Ajuste no get_by_id
    old_get_by_id = """            for row in batch_rows:
                batches_dict[row['batch_code']] = Batch(
                    code=row['batch_code'], product_id=row['product_id'], quantity=row['quantity'],
                    expiration_date=row['expiration_date'], warehouse_id=row.get('warehouse_id', 'WH-PADRAO'),
                    location_id=row.get('location_id', ''), manufacturing_date=row['manufacturing_date'],
                    supplier=row['supplier'], status=row['status'], traceability_id=row['traceability_id']
                )"""
                
    new_get_by_id = """            for row in batch_rows:
                row_dict = dict(row)
                batches_dict[row_dict['batch_code']] = Batch(
                    code=row_dict['batch_code'], product_id=row_dict['product_id'], quantity=row_dict['quantity'],
                    expiration_date=row_dict['expiration_date'], warehouse_id=row_dict.get('warehouse_id', 'WH-PADRAO'),
                    location_id=row_dict.get('location_id', ''), manufacturing_date=row_dict['manufacturing_date'],
                    supplier=row_dict['supplier'], status=row_dict['status'], traceability_id=row_dict['traceability_id']
                )"""

    # 2. Ajuste no get_all
    old_get_all = """                for b in batch_rows:
                    batches_dict[b['batch_code']] = Batch(
                        code=b['batch_code'], product_id=b['product_id'], quantity=b['quantity'],
                        expiration_date=b['expiration_date'], warehouse_id=b.get('warehouse_id', 'WH-PADRAO'),
                        location_id=b.get('location_id', ''), manufacturing_date=b['manufacturing_date'],
                        supplier=b['supplier'], status=b['status'], traceability_id=b['traceability_id']
                    )"""
                    
    new_get_all = """                for b in batch_rows:
                    b_dict = dict(b)
                    batches_dict[b_dict['batch_code']] = Batch(
                        code=b_dict['batch_code'], product_id=b_dict['product_id'], quantity=b_dict['quantity'],
                        expiration_date=b_dict['expiration_date'], warehouse_id=b_dict.get('warehouse_id', 'WH-PADRAO'),
                        location_id=b_dict.get('location_id', ''), manufacturing_date=b_dict['manufacturing_date'],
                        supplier=b_dict['supplier'], status=b_dict['status'], traceability_id=b_dict['traceability_id']
                    )"""

    content = content.replace(old_get_by_id, new_get_by_id)
    content = content.replace(old_get_all, new_get_all)
    return content

try:
    with SafeRefactor("src/interfaces/sqlite_repository.py") as sr:
        sr.apply(patch_row_get_incompatibility)
except Exception as e:
    print(f"Falha ao estabilizar Repositorio: {e}")
    sys.exit(1)
KIPPE_HUNK
python3 "${KIPPE_ROOT}/install/sprints/hotfix_sqlite_row.py"

kippe::step 2 ${TOTAL_STEPS} "Expanding Semantic Gate to Prevent Future SQLite Row Methods Corruption..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/sprints/upgrade_semantic_gate.py"
import os
import sys
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor

def inject_row_anti_pattern(content: str) -> str:
    anti_pattern_logic = """
            row_get_pattern = re.compile(r'row\.get\(')
            b_get_pattern = re.compile(r'b\.get\(')
            
            # Bloqueia chamadas .get() diretas se a var parecer ser sqlite3.Row em contextos de repositório
            if 'sqlite_repository.py' in filepath.name:
                row_gets = row_get_pattern.findall(content)
                b_gets = b_get_pattern.findall(content)
                if row_gets or b_gets:
                    print(f"[SEMANTIC FATAL] Incompatibilidade API detectada. 'sqlite3.Row' nao suporta .get(). Converta para dict() antes em: {filepath.name}")
                    has_errors = True
"""
    if "row.get" not in content and "b.get" not in content:
        content = content.replace(
            "invalid_comps = invalid_as_pattern.findall(content)",
            anti_pattern_logic + "\n            invalid_comps = invalid_as_pattern.findall(content)"
        )
    return content

try:
    with SafeRefactor("install/lib/semantic_validator.py") as sr:
        sr.apply(inject_row_anti_pattern)
except Exception as e:
    sys.exit(1)
KIPPE_HUNK
python3 "${KIPPE_ROOT}/install/sprints/upgrade_semantic_gate.py"

kippe::step 3 ${TOTAL_STEPS} "Preflight: Semantic Validator & AST Compilation Gate..."
# Recarrega bootstrap para garantir variaveis
source "${KIPPE_ROOT}/install/lib/bootstrap.sh"
kippe::validate_script_syntax "${BASH_SOURCE[0]}"

kippe::step 4 ${TOTAL_STEPS} "Executing Core Suite Regression (Ensuring GREEN State)..."
kippe::test_execute_all

kippe::step 5 ${TOTAL_STEPS} "Syncing Governance State (Completing INF005 Pipeline)..."
# Limpeza de scripts de infraestrutura transientes
rm -f "${KIPPE_ROOT}"/install/sprints/hotfix_*.py
rm -f "${KIPPE_ROOT}"/install/sprints/upgrade_*.py
rm -f data/test_*.db data/test_*.log data/test_*.db-journal 2>/dev/null || true

kippe::checkpoint_create "044" "1.2.0-gov" "INF005.2" "SUCCESS"
kippe::manifest_create "INF005.2" "INF" "1.2.0-gov" "SUCCESS" "INV010"

# Executa o Governance Pipeline gerando o PROJECT_STATE.json mecanicamente
kippe::governance_sync \
    "C" \
    "Inventory" \
    "2" \
    "Profissional" \
    "INF005.2 (Row Hotfix)" \
    "INV009 — Stock Transfers" \
    "9/20" \
    "49" \
    "0" \
    "STABLE"

exit 0

