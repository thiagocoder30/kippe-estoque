#!/usr/bin/env bash
set -Eeuo pipefail
# -----------------------------------------------------------------------------
# Repository Root Resolution & Framework Init
# -----------------------------------------------------------------------------
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
readonly FRAMEWORK_VERSION="1.0.0"
kippe::init() {
    local lib_dir="${KIPPE_ROOT}/install/lib"
    
    if [[ ! -f "${lib_dir}/testing.sh" ]] || [[ ! -f "${lib_dir}/validation.sh" ]]; then
        echo "[ERROR] Falha crítica de inicialização: Bibliotecas core não encontradas em ${lib_dir}."
        exit 1
    fi
    
    source "${lib_dir}/testing.sh"
    source "${lib_dir}/validation.sh"
    
    echo "  -> Bootstrap: KIPPE_ROOT resolved to [${KIPPE_ROOT}]"
}
kippe::init_environment() {
    export KIPPE_LOG_DIR="${KIPPE_ROOT}/reports/logs"
    mkdir -p "${KIPPE_LOG_DIR}"
}
kippe::banner_program() {
    echo -e "\n============================================================"
    echo -e " KIPPE PLATFORM - PROGRAM $1"
    echo -e " SPRINT $2: $3"
    echo -e "============================================================\n"
}
kippe::step() {
    echo -e "\n[Step $1/$2] $3"
}
kippe::success() {
    echo -e "\n[SUCCESS] $1"
}
kippe::error() {
    echo -e "\n[ERROR] $1"
}
kippe::banner_finish() {
    echo -e "\n------------------------------------------------------------"
    echo -e " SPRINT EXECUTION FINISHED"
    echo -e "------------------------------------------------------------"
}
kippe::on_error() {
    echo -e "\n[CRITICAL FATAL] Execution failed at line $1"
    exit 1
}
kippe::checkpoint_create() {
    local id="$1"
    local version="$2"
    local sprint="$3"
    local status="$4"
    mkdir -p "${KIPPE_ROOT}/docs/checkpoints"
    echo "${id}|${version}|${sprint}|${status}|$(date -u +"%Y-%m-%dT%H:%M:%SZ")" > "${KIPPE_ROOT}/docs/checkpoints/CHK-${id}.txt"
}
kippe::manifest_create() {
    local sprint="$1"
    local program="$2"
    local version="$3"
    local status="$4"
    local next_sprint="$5"
    mkdir -p "${KIPPE_ROOT}/reports"
    cat <<EOF > "${KIPPE_ROOT}/reports/SPRINT_MANIFEST_${sprint}.json"
{
  "sprint": "${sprint}",
  "program": "${program}",
  "version": "${version}",
  "status": "${status}",
  "next_sprint": "${next_sprint}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
}
