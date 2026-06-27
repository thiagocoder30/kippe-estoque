#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A
# SPRINT A000.1.5
# FILE IDENTITY LAYER
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
    "A000.1.5" \
    "File Identity Layer"

# ============================================================
# STEP 1 — DEFINE RUNTIME PATHS
# ============================================================
kippe::step 1 ${TOTAL_STEPS} "Defining runtime paths..."

KIPPE_RUNTIME_LOG_DIR="${ROOT}/reports/logs"
KIPPE_EXPORT_ROOT="/sdcard/Download/KIPPE"
KIPPE_EXTERNAL_LOGS="${KIPPE_EXPORT_ROOT}/logs"

mkdir -p "${KIPPE_RUNTIME_LOG_DIR}"
mkdir -p "${KIPPE_EXTERNAL_LOGS}"

# ============================================================
# STEP 2 — CREATE TEST LOGS
# ============================================================
kippe::step 2 ${TOTAL_STEPS} "Creating test logs..."

echo "test-identity-1" > "${KIPPE_RUNTIME_LOG_DIR}/identity-1.log"
echo "test-identity-2" > "${KIPPE_RUNTIME_LOG_DIR}/identity-2.log"

# ============================================================
# STEP 3 — FILE IDENTITY EXPORT ENGINE
# ============================================================
kippe::step 3 ${TOTAL_STEPS} "Executing inode-safe export..."

kippe::export_logs() {
    local src_dir="${KIPPE_RUNTIME_LOG_DIR}"
    local dst_dir="${KIPPE_EXTERNAL_LOGS}"

    [[ ! -d "$src_dir" ]] && return 0
    mkdir -p "$dst_dir"

    find "$src_dir" -type f -name "*.log" | while read -r file; do
        local filename
        filename="$(basename "$file")"

        local dest_file="${dst_dir}/${filename}"

        # inode check (REAL identity)
        if [[ -e "$dest_file" ]]; then
            src_inode="$(stat -c '%i' "$file" 2>/dev/null || echo "")"
            dst_inode="$(stat -c '%i' "$dest_file" 2>/dev/null || echo "")"

            if [[ -n "$src_inode" && "$src_inode" == "$dst_inode" ]]; then
                continue
            fi
        fi

        cp -f "$file" "$dest_file"
    done
}

# ============================================================
# STEP 4 — RUN EXPORT
# ============================================================
kippe::step 4 ${TOTAL_STEPS} "Running identity-safe export..."
kippe::export_logs

# ============================================================
# STEP 5 — VALIDATION
# ============================================================
kippe::step 5 ${TOTAL_STEPS} "Validating exported files..."

for f in "${KIPPE_RUNTIME_LOG_DIR}"/*.log; do
    name="$(basename "$f")"
    [[ -f "${KIPPE_EXTERNAL_LOGS}/${name}" ]] || {
        echo "[FATAL] Missing export: $name"
        exit 1
    }
done

# ============================================================
# STEP 6 — CLEANUP
# ============================================================
kippe::step 6 ${TOTAL_STEPS} "Cleaning test artifacts..."

rm -f "${KIPPE_RUNTIME_LOG_DIR}/identity-"*.log

kippe::banner_finish

kippe::success "File Identity Layer successfully installed."

echo
echo "Next Sprint: A000.2 — Templates Institucionais"
echo
