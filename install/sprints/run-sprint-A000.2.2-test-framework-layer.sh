#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A
# SPRINT A000.2.2
# ADVANCED TEST FRAMEWORK LAYER
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
    "A000.2.2" \
    "Advanced Test Framework Layer"

# ============================================================
# STEP 1 — TEST REGISTRY
# ============================================================
kippe::step 1 ${TOTAL_STEPS} "Initializing test registry..."

KIPPE_TEST_DIR="${ROOT}/reports/tests"
mkdir -p "${KIPPE_TEST_DIR}"

TEST_ID="A000.2.2"

# ============================================================
# STEP 2 — DEFINE EXPECTED STATE
# ============================================================
kippe::step 2 ${TOTAL_STEPS} "Defining expected state..."

EXPECTED_FILES=(
    "reports/logs"
    "/sdcard/Download/KIPPE/logs"
)

# ============================================================
# STEP 3 — RUN SAMPLE SPRINT BEHAVIOR
# ============================================================
kippe::step 3 ${TOTAL_STEPS} "Executing sample workflow..."

KIPPE_RUNTIME_LOG_DIR="${ROOT}/reports/logs"
mkdir -p "${KIPPE_RUNTIME_LOG_DIR}"

echo "test-framework-log" > "${KIPPE_RUNTIME_LOG_DIR}/framework.log"

kippe::export_logs

# ============================================================
# STEP 4 — ASSERTION ENGINE
# ============================================================
kippe::step 4 ${TOTAL_STEPS} "Running assertions..."

ASSERT_FAIL=0

for path in "${EXPECTED_FILES[@]}"; do
    if [[ "$path" == "/sdcard/Download/KIPPE/logs" ]]; then
        if [[ ! -d "$path" ]]; then
            echo "[ASSERT FAIL] Missing export directory: $path"
            ASSERT_FAIL=1
        fi
    else
        if [[ ! -d "${ROOT}/$path" ]]; then
            echo "[ASSERT FAIL] Missing runtime directory: $path"
            ASSERT_FAIL=1
        fi
    fi
done

# ============================================================
# STEP 5 — FILE ASSERTION (STRICT)
# ============================================================
kippe::step 5 ${TOTAL_STEPS} "Validating exported artifacts..."

if [[ ! -f "${KIPPE_RUNTIME_LOG_DIR}/framework.log" ]]; then
    echo "[ASSERT FAIL] Missing runtime log"
    ASSERT_FAIL=1
fi

if [[ ! -f "/sdcard/Download/KIPPE/logs/framework.log" ]]; then
    echo "[ASSERT FAIL] Missing exported log"
    ASSERT_FAIL=1
fi

# ============================================================
# STEP 6 — INTEGRITY CHECK
# ============================================================
kippe::step 6 ${TOTAL_STEPS} "Validating data integrity..."

if [[ -f "${KIPPE_RUNTIME_LOG_DIR}/framework.log" && -f "/sdcard/Download/KIPPE/logs/framework.log" ]]; then
    src_hash="$(sha256sum "${KIPPE_RUNTIME_LOG_DIR}/framework.log" | awk '{print $1}')"
    dst_hash="$(sha256sum "/sdcard/Download/KIPPE/logs/framework.log" | awk '{print $1}')"

    if [[ "$src_hash" != "$dst_hash" ]]; then
        echo "[ASSERT FAIL] Hash mismatch detected"
        ASSERT_FAIL=1
    fi
fi

# ============================================================
# STEP 7 — TEST RESULT
# ============================================================
kippe::step 7 ${TOTAL_STEPS} "Finalizing test result..."

if [[ "$ASSERT_FAIL" -eq 0 ]]; then
    RESULT="PASS"
else
    RESULT="FAIL"
fi

mkdir -p "${KIPPE_TEST_DIR}"

cat > "${KIPPE_TEST_DIR}/${TEST_ID}.json" <<EOF
{
  "test_id": "${TEST_ID}",
  "result": "${RESULT}",
  "timestamp": "$(date +%s)"
}
EOF

# ============================================================
# STEP 8 — SUMMARY
# ============================================================
kippe::step 8 ${TOTAL_STEPS} "Generating test summary..."

kippe::banner_finish

echo "======================================"
echo "SPRINT TEST RESULT"
echo "ID: ${TEST_ID}"
echo "RESULT: ${RESULT}"
echo "======================================"

if [[ "$RESULT" != "PASS" ]]; then
    exit 1
fi

echo
echo "Next Stage: A000.2.3 — Regression Guard Layer"
echo
