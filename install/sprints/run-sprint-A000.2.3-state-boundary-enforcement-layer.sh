#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A
# SPRINT A000.2.3
# STATE BOUNDARY ENFORCEMENT LAYER
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
    "A000.2.3" \
    "State Boundary Enforcement Layer"

# ============================================================
# STEP 1 — DEFINE BOUNDARIES
# ============================================================
kippe::step 1 ${TOTAL_STEPS} "Defining system boundaries..."

KIPPE_RUNTIME_DIR="${ROOT}/reports/logs"
KIPPE_EXPORT_DIR="$(kippe::export_root)/logs"

mkdir -p "${KIPPE_RUNTIME_DIR}"
mkdir -p "${KIPPE_EXPORT_DIR}"

# ============================================================
# STEP 2 — HARD BOUNDARY GUARDS
# ============================================================
kippe::step 2 ${TOTAL_STEPS} "Initializing boundary guards..."

kippe::assert_different_paths() {
    local a b
    a="$(realpath "$1" 2>/dev/null || echo "$1")"
    b="$(realpath "$2" 2>/dev/null || echo "$2")"

    if [[ "$a" == "$b" ]]; then
        echo "[FATAL] Boundary violation detected:"
        echo "SOURCE = $a"
        echo "DEST   = $b"
        exit 1
    fi
}

export -f kippe::assert_different_paths

kippe::assert_runtime_source() {
    local file="$1"

    local runtime_root="${KIPPE_RUNTIME_DIR}"

    case "$file" in
        "$runtime_root"/*) return 0 ;;
        *)
            echo "[FATAL] Invalid runtime source outside boundary: $file"
            exit 1
        ;;
    esac
}

# ============================================================
# STEP 3 — TEST DATA
# ============================================================
kippe::step 3 ${TOTAL_STEPS} "Creating boundary test log..."

RUNTIME_FILE="${KIPPE_RUNTIME_DIR}/boundary.log"
echo "boundary-test" > "$RUNTIME_FILE"

# ============================================================
# STEP 4 — PRE-EXPORT VALIDATION
# ============================================================
kippe::step 4 ${TOTAL_STEPS} "Validating export boundaries..."

kippe::assert_runtime_source "$RUNTIME_FILE"
kippe::assert_different_paths "$RUNTIME_FILE" "${KIPPE_EXPORT_DIR}/boundary.log"

# ============================================================
# STEP 5 — SAFE EXPORT (ENFORCED)
# ============================================================
kippe::step 5 ${TOTAL_STEPS} "Executing boundary-safe export..."

DEST_FILE="${KIPPE_EXPORT_DIR}/boundary.log"

if [[ "$(realpath "$RUNTIME_FILE")" == "$(realpath "$DEST_FILE" 2>/dev/null || echo "$DEST_FILE")" ]]; then
    echo "[SKIP] Self-copy prevented"
else
    cp -f "$RUNTIME_FILE" "$DEST_FILE"
fi

# ============================================================
# STEP 6 — VALIDATION
# ============================================================
kippe::step 6 ${TOTAL_STEPS} "Validating boundary integrity..."

if [[ ! -f "$DEST_FILE" ]]; then
    echo "[FATAL] Export failed"
    exit 1
fi

src_hash="$(sha256sum "$RUNTIME_FILE" | awk '{print $1}')"
dst_hash="$(sha256sum "$DEST_FILE" | awk '{print $1}')"

if [[ "$src_hash" != "$dst_hash" ]]; then
    echo "[FATAL] Boundary corruption detected"
    exit 1
fi

# ============================================================
# STEP 7 — FINALIZATION
# ============================================================
kippe::step 7 ${TOTAL_STEPS} "Finalizing boundary enforcement..."

rm -f "$RUNTIME_FILE"

kippe::banner_finish

kippe::success "State Boundary Enforcement Layer active."

echo
echo "Next Stage: A000.3 — Full Test Automation System"
echo
