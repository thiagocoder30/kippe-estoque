#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A
# SPRINT A000.2
# CONTRACT TEMPLATES LAYER
# ============================================================

set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${ROOT}"

export KIPPE_ROOT="${ROOT}"

source install/lib/bootstrap.sh
source install/lib/export.sh

kippe::init
kippe::init_environment
kippe::export_init

trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=8

kippe::banner_program \
    "A" \
    "A000.2" \
    "Contract Templates Layer"

# ============================================================
# STEP 1 — CONTRACT DEFINITION
# ============================================================
kippe::step 1 ${TOTAL_STEPS} "Defining sprint contract..."

KIPPE_SPRINT_ID="A000.2"
KIPPE_SPRINT_TYPE="INSTITUTIONAL_TEMPLATES"

KIPPE_INPUTS=("bootstrap.sh" "export.sh")
KIPPE_OUTPUTS=("reports" "/sdcard/Download/KIPPE")

KIPPE_SIDE_EFFECTS=("filesystem_write" "log_generation" "export_snapshot")

# ============================================================
# STEP 2 — PRE-CONTRACT VALIDATION
# ============================================================
kippe::step 2 ${TOTAL_STEPS} "Validating pre-conditions..."

for dir in "${KIPPE_INPUTS[@]}"; do
    if [[ ! -e "${ROOT}/${dir}" ]]; then
        echo "[FATAL] Missing required input: ${dir}"
        exit 1
    fi
done

# ============================================================
# STEP 3 — RUNTIME INITIALIZATION
# ============================================================
kippe::step 3 ${TOTAL_STEPS} "Initializing controlled runtime..."

KIPPE_RUNTIME_LOG_DIR="${ROOT}/reports/logs"
mkdir -p "${KIPPE_RUNTIME_LOG_DIR}"

# ============================================================
# STEP 4 — EXECUTION PHASE
# ============================================================
kippe::step 4 ${TOTAL_STEPS} "Executing controlled workflow..."

echo "[CONTRACT] Sprint ${KIPPE_SPRINT_ID} executing..."

# simula carga institucional
echo "contract-test-log" > "${KIPPE_RUNTIME_LOG_DIR}/contract.log"

kippe::export_logs

# ============================================================
# STEP 5 — SIDE EFFECT CAPTURE
# ============================================================
kippe::step 5 ${TOTAL_STEPS} "Capturing side effects..."

GENERATED_FILES=$(find "${KIPPE_RUNTIME_LOG_DIR}" -type f)

for file in $GENERATED_FILES; do
    echo "[EFFECT] $(basename "$file") generated"
done

# ============================================================
# STEP 6 — OUTPUT VALIDATION
# ============================================================
kippe::step 6 ${TOTAL_STEPS} "Validating outputs..."

for out in "${KIPPE_OUTPUTS[@]}"; do
    if [[ "$out" == "/sdcard/Download/KIPPE" ]]; then
        if [[ ! -d "$out" ]]; then
            echo "[FATAL] Missing export root: $out"
            exit 1
        fi
    fi
done

# ============================================================
# STEP 7 — CONTRACT SUMMARY
# ============================================================
kippe::step 7 ${TOTAL_STEPS} "Generating contract summary..."

echo "========================================"
echo "SPRINT CONTRACT SUMMARY"
echo "ID: ${KIPPE_SPRINT_ID}"
echo "TYPE: ${KIPPE_SPRINT_TYPE}"
echo "INPUTS: ${KIPPE_INPUTS[*]}"
echo "OUTPUTS: ${KIPPE_OUTPUTS[*]}"
echo "SIDE EFFECTS: ${KIPPE_SIDE_EFFECTS[*]}"
echo "========================================"

# ============================================================
# STEP 8 — FINALIZE
# ============================================================
kippe::step 8 ${TOTAL_STEPS} "Finalizing contract execution..."

rm -f "${KIPPE_RUNTIME_LOG_DIR}/contract.log"

kippe::banner_finish

kippe::success "Contract Templates Layer successfully installed."

echo
echo "Next Stage: A000.3 — Test Framework Layer"
echo
