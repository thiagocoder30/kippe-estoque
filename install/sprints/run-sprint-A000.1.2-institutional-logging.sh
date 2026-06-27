#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A
# SPRINT A000.1.2 (INSTITUTIONAL)
# LOG ARCHITECTURE STABILIZATION
# ============================================================

set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${ROOT}"

export KIPPE_ROOT="${ROOT}"

# IMPORTANTE:
# NÃO sobrescreve bootstrap. Apenas override seguro de runtime
export KIPPE_LOG_DIR="${ROOT}/reports/logs"

source install/lib/bootstrap.sh
source install/lib/export.sh

kippe::init
kippe::init_environment
kippe::export_init

trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=7

kippe::banner_program \
    "A" \
    "A000.1.2" \
    "Institutional Logging Architecture"

# ============================================================
# STEP 1 — VALIDATION
# ============================================================
kippe::step 1 ${TOTAL_STEPS} "Validating immutable core..."
kippe::validate_environment

# ============================================================
# STEP 2 — ENSURE LOCAL LOG STRUCTURE
# ============================================================
kippe::step 2 ${TOTAL_STEPS} "Ensuring local log lifecycle structure..."
mkdir -p "${KIPPE_LOG_DIR}"

# ============================================================
# STEP 3 — REMOVE ALL BOOTSTRAP PATCHING (CRITICAL CHANGE)
# ============================================================
kippe::step 3 ${TOTAL_STEPS} "Verifying no core mutation policy..."

# apenas valida, não modifica
if grep -q "sed .*bootstrap" install/sprints/run-sprint-A000.1.1* 2>/dev/null; then
    echo "[WARN] Legacy bootstrap patching detected in history (ignored)."
fi

# ============================================================
# STEP 4 — CREATE TEST LOG
# ============================================================
kippe::step 4 ${TOTAL_STEPS} "Creating lifecycle test log..."
TEST_LOG="${KIPPE_LOG_DIR}/institutional-test.log"
touch "${TEST_LOG}"

# ============================================================
# STEP 5 — EXPORT FLOW (IDEMPOTENT)
# ============================================================
kippe::step 5 ${TOTAL_STEPS} "Executing export layer..."
kippe::export_logs

# ============================================================
# STEP 6 — VALIDATE SEPARATION (CRITICAL CHECK)
# ============================================================
kippe::step 6 ${TOTAL_STEPS} "Validating source/destination separation..."

SRC="${KIPPE_LOG_DIR}"
DST="${KIPPE_EXTERNAL_LOGS:-/sdcard/Download/KIPPE/logs}"

if [[ "${SRC}" == "${DST}" ]]; then
    echo "[FATAL] Architecture violation: SRC == DST"
    exit 1
fi

# ============================================================
# STEP 7 — CLEANUP TEST ARTIFACT
# ============================================================
rm -f "${TEST_LOG}"

kippe::banner_finish

kippe::success \
"Institutional logging architecture stabilized."

echo
echo "Next Sprint: A000.2 — Templates Institucionais"
echo
