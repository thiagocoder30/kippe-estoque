#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A
# SPRINT A000.2.1
# CONTRACT BINDING LAYER
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
    "A000.2.1" \
    "Contract Binding Layer"

# ============================================================
# STEP 1 — CONTRACT BINDING TABLE (CORE INNOVATION)
# ============================================================
kippe::step 1 ${TOTAL_STEPS} "Defining contract binding table..."

# formato: "alias:path_real"
KIPPE_CONTRACT_BINDINGS=(
    "bootstrap:install/lib/bootstrap.sh"
    "export:install/lib/export.sh"
    "logs_dir:reports/logs"
)

# ============================================================
# STEP 2 — BINDING RESOLVER ENGINE
# ============================================================
kippe::step 2 ${TOTAL_STEPS} "Initializing binding resolver..."

kippe::resolve_binding() {
    local key="$1"

    for entry in "${KIPPE_CONTRACT_BINDINGS[@]}"; do
        local alias="${entry%%:*}"
        local path="${entry##*:}"

        if [[ "$alias" == "$key" ]]; then
            echo "${ROOT}/${path}"
            return 0
        fi
    done

    echo "[FATAL] Unknown contract binding: $key"
    exit 1
}

export -f kippe::resolve_binding

# ============================================================
# STEP 3 — CONTRACT INPUT VALIDATION (FIXED MODEL)
# ============================================================
kippe::step 3 ${TOTAL_STEPS} "Validating contract inputs..."

KIPPE_CONTRACT_INPUTS=(
    "bootstrap"
    "export"
)

for input in "${KIPPE_CONTRACT_INPUTS[@]}"; do
    resolved_path="$(kippe::resolve_binding "$input")"

    if [[ ! -e "$resolved_path" ]]; then
        echo "[FATAL] Missing contract input: $input -> $resolved_path"
        exit 1
    fi
done

# ============================================================
# STEP 4 — RUNTIME INITIALIZATION
# ============================================================
kippe::step 4 ${TOTAL_STEPS} "Initializing runtime environment..."

KIPPE_RUNTIME_LOG_DIR="$(kippe::resolve_binding logs_dir)"
mkdir -p "${KIPPE_RUNTIME_LOG_DIR}"

# ============================================================
# STEP 5 — EXECUTION TEST
# ============================================================
kippe::step 5 ${TOTAL_STEPS} "Executing contract-bound workflow..."

echo "contract-binding-test" > "${KIPPE_RUNTIME_LOG_DIR}/binding.log"

kippe::export_logs

# ============================================================
# STEP 6 — VALIDATION OF BINDING INTEGRITY
# ============================================================
kippe::step 6 ${TOTAL_STEPS} "Validating binding integrity..."

BOOTSTRAP_PATH="$(kippe::resolve_binding bootstrap)"
EXPORT_PATH="$(kippe::resolve_binding export)"

if [[ "$BOOTSTRAP_PATH" == "$EXPORT_PATH" ]]; then
    echo "[FATAL] Binding collision detected"
    exit 1
fi

# ============================================================
# STEP 7 — FINALIZATION
# ============================================================
kippe::step 7 ${TOTAL_STEPS} "Finalizing contract binding layer..."

rm -f "${KIPPE_RUNTIME_LOG_DIR}/binding.log"

kippe::banner_finish

kippe::success "Contract Binding Layer successfully installed."

echo
echo "Next Stage: A000.3 — Test Framework Layer"
echo
