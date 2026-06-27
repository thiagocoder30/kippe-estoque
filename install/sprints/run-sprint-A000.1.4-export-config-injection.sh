#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A
# SPRINT A000.1.4
# EXPORT CONFIG INJECTION FIX
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

TOTAL_STEPS=7

kippe::banner_program \
    "A" \
    "A000.1.4" \
    "Export Config Injection Fix"

# ============================================================
# STEP 1 — DEFINE RUNTIME CONFIG (SOURCE OF TRUTH)
# ============================================================
kippe::step 1 ${TOTAL_STEPS} "Defining runtime configuration layer..."

KIPPE_RUNTIME_LOG_DIR="${ROOT}/reports/logs"
KIPPE_EXPORT_ROOT="/sdcard/Download/KIPPE"

KIPPE_EXTERNAL_LOGS="${KIPPE_EXPORT_ROOT}/logs"
KIPPE_EXTERNAL_MANIFESTS="${KIPPE_EXPORT_ROOT}/manifests"
KIPPE_EXTERNAL_CHECKPOINTS="${KIPPE_EXPORT_ROOT}/checkpoints"

# ============================================================
# STEP 2 — ENSURE LOCAL STRUCTURE
# ============================================================
kippe::step 2 ${TOTAL_STEPS} "Ensuring runtime log directory..."
mkdir -p "${KIPPE_RUNTIME_LOG_DIR}"

# ============================================================
# STEP 3 — CREATE TEST LOG
# ============================================================
kippe::step 3 ${TOTAL_STEPS} "Creating test runtime log..."
TEST_LOG="${KIPPE_RUNTIME_LOG_DIR}/inject-test.log"
touch "${TEST_LOG}"

# ============================================================
# STEP 4 — INJECT CONFIG INTO EXPORT LAYER (CRITICAL FIX)
# ============================================================
kippe::step 4 ${TOTAL_STEPS} "Injecting runtime config into export layer..."

# override explícito de runtime → export context
export KIPPE_LOG_DIR="${KIPPE_RUNTIME_LOG_DIR}"
export KIPPE_EXTERNAL_LOGS="${KIPPE_EXTERNAL_LOGS}"
export KIPPE_EXTERNAL_MANIFESTS="${KIPPE_EXTERNAL_MANIFESTS}"
export KIPPE_EXTERNAL_CHECKPOINTS="${KIPPE_EXTERNAL_CHECKPOINTS}"

# ============================================================
# STEP 5 — VALIDATE PHYSICAL SEPARATION
# ============================================================
kippe::step 5 ${TOTAL_STEPS} "Validating injection consistency..."

SRC="$(realpath "${KIPPE_LOG_DIR}" 2>/dev/null || echo "${KIPPE_LOG_DIR}")"
DST="$(realpath "${KIPPE_EXTERNAL_LOGS}" 2>/dev/null || echo "${KIPPE_EXTERNAL_LOGS}")"

if [[ "${SRC}" == "${DST}" ]]; then
    echo "[FATAL] Export Injection Failure: runtime == export"
    exit 1
fi

# ============================================================
# STEP 6 — EXECUTE EXPORT
# ============================================================
kippe::step 6 ${TOTAL_STEPS} "Executing injected export..."
kippe::export_logs

# ============================================================
# STEP 7 — CLEANUP
# ============================================================
kippe::step 7 ${TOTAL_STEPS} "Cleaning test artifacts..."

rm -f "${TEST_LOG}"

kippe::banner_finish

kippe::success \
"Export Config Injection Fix successfully applied."

echo
echo "Next Sprint: A000.2 — Templates Institucionais"
echo
