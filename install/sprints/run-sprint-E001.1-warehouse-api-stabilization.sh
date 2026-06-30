#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - SPRINT E001.1: WAREHOUSE API STABILIZATION
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

kippe::banner_program "E" "E001.1" "API Stabilization & Legacy Contract Inspection"

kippe::step 1 3 "Exposing Public API in src/domain/warehouse/__init__.py..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/__init__.py"
from .topology import Warehouse, StorageLocation

__all__ = [
    "Warehouse",
    "StorageLocation",
]
KIPPE_HUNK

kippe::step 2 3 "Inspecting Legacy Contract (test_multi_warehouse.py)..."
# Inspecionando o contrato para garantir que não haja divergências semânticas
echo "--- Conteúdo do Contrato Legado (Primeiras 50 linhas) ---"
sed -n '1,50p' "${KIPPE_ROOT}/tests/test_multi_warehouse.py" || echo "Arquivo legado não encontrado."

kippe::step 3 3 "Running Regression with Legacy Integration..."
# Valida se a exportação resolveu o ImportError e se o teste legado passa
kippe::test_execute_all

# Registro de Governança
kippe::checkpoint_create "090" "1.5.0-platform" "E001.1" "SUCCESS"

echo -e "\n[STATUS] API do Bounded Context Warehouse estabilizada e compatibilidade legada verificada."
exit 0

