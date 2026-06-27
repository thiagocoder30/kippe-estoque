#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A
# SPRINT A000.1.6
# ATOMIC EXPORT LAYER (FUSE-SAFE)
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

TOTAL_STEPS=6

kippe::banner_program \
    "A" \
    "A000.1.6" \
    "Atomic Export Layer"

# ============================================================
# STEP 1 — RUNTIME PATHS
# ============================================================
kippe::step 1 ${TOTAL_STEPS} "Initializing runtime paths..."

KIPPE_RUNTIME_LOG_DIR="${ROOT}/reports/logs"
KIPPE_EXPORT_ROOT="/sdcard/Download/KIPPE"
KIPPE_EXTERNAL_LOGS="${KIPPE_EXPORT_ROOT}/logs"

mkdir -p "${KIPPE_RUNTIME_LOG_DIR}"
mkdir -p "${KIPPE_EXTERNAL_LOGS}"

# ============================================================
# STEP 2 — CREATE TEST DATA
# ============================================================
kippe::step 2 ${TOTAL_STEPS} "Creating test logs..."

echo "atomic-test-1" > "${KIPPE_RUNTIME_LOG_DIR}/atomic-1.log"
echo "atomic-test-2" > "${KIPPE_RUNTIME_LOG_DIR}/atomic-2.log"

# ============================================================
# STEP 3 — ATOMIC EXPORT ENGINE (CORE FIX)
# ============================================================
kippe::step 3 ${TOTAL_STEPS} "Executing atomic export engine..."

kippe::export_logs() {
    local src="${KIPPE_RUNTIME_LOG_DIR}"
    local dst="${KIPPE_EXTERNAL_LOGS}"

    mkdir -p "$dst"

    find "$src" -type f -name "*.log" | while read -r file; do
        local name tmp final
        name="$(basename "$file")"

        tmp="${dst}/.${name}.tmp"
        final="${dst}/${name}"

        # evita export desnecessário (inode-safe check opcional)
        if [[ -f "$final" ]]; then
            src_sum="$(stat -c '%s' "$file" 2>/dev/null || echo 0)"
            dst_sum="$(stat -c '%s' "$final" 2>/dev/null || echo 0)"

            if [[ "$src_sum" -eq "$dst_sum" ]]; then
                continue
            fi
        fi

        # WRITE ATÔMICO (FUSE SAFE)
        cp -f "$file" "$tmp"
        mv -f "$tmp" "$final"
    done
}

# ============================================================
# STEP 4 — RUN EXPORT
# ============================================================
kippe::step 4 ${TOTAL_STEPS} "Running atomic export..."
kippe::export_logs

# ============================================================
# STEP 5 — VALIDATION
# ============================================================
kippe::step 5 ${TOTAL_STEPS} "Validating exported files..."

for f in "${KIPPE_RUNTIME_LOG_DIR}"/*.log; do
    name="$(basename "$f")"

    if [[ ! -f "${KIPPE_EXTERNAL_LOGS}/${name}" ]]; then
        echo "[FATAL] Missing export: $name"
        exit 1
    fi
done

# ============================================================
# STEP 6 — CLEANUP
# ============================================================
kippe::step 6 ${TOTAL_STEPS} "Cleaning test artifacts..."

rm -f "${KIPPE_RUNTIME_LOG_DIR}/atomic-"*.log

kippe::banner_finish

kippe::success "Atomic Export Layer successfully installed."

echo
echo "Next Stage: A000.2 — Advanced Test Framework Layer"
echo
