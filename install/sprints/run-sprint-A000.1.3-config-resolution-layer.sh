#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A
# SPRINT A000.1.3
# CONFIG RESOLUTION LAYER
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
    "A000.1.3" \
    "Config Resolution Layer"

# ============================================================
# STEP 1 — RESOLVER CORE FUNCTION
# ============================================================
kippe::step 1 ${TOTAL_STEPS} "Installing path resolver..."

kippe::resolve_path() {
    local path="$1"
    realpath "$path" 2>/dev/null || echo "$path"
}

export -f kippe::resolve_path

# ============================================================
# STEP 2 — DEFINE CONTROLLED CONFIG
# ============================================================
kippe::step 2 ${TOTAL_STEPS} "Defining controlled configuration layer..."

KIPPE_RUNTIME_LOG_DIR="${ROOT}/reports/logs"
KIPPE_EXPORT_ROOT="/sdcard/Download/KIPPE"

KIPPE_EXTERNAL_LOGS="${KIPPE_EXPORT_ROOT}/logs"
KIPPE_EXTERNAL_MANIFESTS="${KIPPE_EXPORT_ROOT}/manifests"
KIPPE_EXTERNAL_CHECKPOINTS="${KIPPE_EXPORT_ROOT}/checkpoints"

# ============================================================
# STEP 3 — FORCE EXPORT REINIT
# ============================================================
kippe::step 3 ${TOTAL_STEPS} "Reinitializing export layer..."
kippe::export_init

# ============================================================
# STEP 4 — CREATE RUNTIME LOG
# ============================================================
kippe::step 4 ${TOTAL_STEPS} "Creating runtime log..."
mkdir -p "${KIPPE_RUNTIME_LOG_DIR}"
TEST_LOG="${KIPPE_RUNTIME_LOG_DIR}/resolution-layer-test.log"
touch "${TEST_LOG}"

# ============================================================
# STEP 5 — ENFORCE PHYSICAL SEPARATION
# ============================================================
kippe::step 5 ${TOTAL_STEPS} "Validating physical path separation..."

SRC="$(kippe::resolve_path "${KIPPE_RUNTIME_LOG_DIR}")"
DST="$(kippe::resolve_path "${KIPPE_EXTERNAL_LOGS}")"

if [[ "${SRC}" == "${DST}" ]]; then
    echo "[FATAL] Config Resolution Failure: runtime == export"
    exit 1
fi

# ============================================================
# STEP 6 — EXPORT TEST
# ============================================================
kippe::step 6 ${TOTAL_STEPS} "Testing export layer..."
kippe::export_logs

# ============================================================
# STEP 7 — CLEANUP
# ============================================================
kippe::step 7 ${TOTAL_STEPS} "Cleaning test artifacts..."
rm -f "${TEST_LOG}"

# ============================================================
# STEP 8 — FINALIZE
# ============================================================
kippe::step 8 ${TOTAL_STEPS} "Finalizing configuration layer..."

kippe::banner_finish

kippe::success \
"Config Resolution Layer successfully installed."

echo
echo "Next Sprint: A000.2 — Templates Institucionais"
echo
