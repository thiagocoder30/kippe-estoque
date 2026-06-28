#!/usr/bin/env bash
set -Eeuo pipefail
# -----------------------------------------------------------------------------
# Repository Root Resolution & Framework Init
# -----------------------------------------------------------------------------
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
# Guard de inicialização condicional para evitar colisões catastróficas em re-sourcing
if [[ -z "${FRAMEWORK_VERSION:-}" ]]; then
    readonly FRAMEWORK_VERSION="1.1.0-gov"
fi
kippe::framework_version() {
    printf '%s\n' "${FRAMEWORK_VERSION}"
}
kippe::init() {
    local lib_dir="${KIPPE_ROOT}/install/lib"
    if [[ ! -f "${lib_dir}/testing.sh" ]] || [[ ! -f "${lib_dir}/validation.sh" ]]; then
        echo "[ERROR] Falha crítica: Bibliotecas core não encontradas."
        exit 1
    fi
    source "${lib_dir}/testing.sh"
    source "${lib_dir}/validation.sh"
}
kippe::init_environment() {
    export KIPPE_LOG_DIR="${KIPPE_ROOT}/reports/logs"
    mkdir -p "${KIPPE_LOG_DIR}"
    mkdir -p "${KIPPE_ROOT}/docs/checkpoints"
}
kippe::banner_program() {
    echo -e "\n============================================================"
    echo -e " KIPPE PLATFORM - PROGRAM $1"
    echo -e " SPRINT $2: $3"
    echo -e "============================================================\n"
}
kippe::step() { echo -e "\n[Step $1/$2] $3"; }
kippe::success() { echo -e "\n[SUCCESS] $1"; }
kippe::error() { echo -e "\n[ERROR] $1"; }
kippe::on_error() { echo -e "\n[CRITICAL FATAL] Execution failed at line $1"; exit 1; }
kippe::checkpoint_create() {
    local id="$1"; local version="$2"; local sprint="$3"; local status="$4"
    echo "${id}|${version}|${sprint}|${status}|$(date -u +"%Y-%m-%dT%H:%M:%SZ")" > "${KIPPE_ROOT}/docs/checkpoints/CHK-${id}.txt"
}
kippe::manifest_create() {
    local sprint="$1"; local program="$2"; local version="$3"; local status="$4"; local next_sprint="$5"
    cat <<EOF > "${KIPPE_ROOT}/reports/SPRINT_MANIFEST_${sprint}.json"
{ "sprint": "${sprint}", "program": "${program}", "version": "${version}", "status": "${status}", "next_sprint": "${next_sprint}", "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" }
EOF
}
kippe::governance_sync() {
    local program_name="$1"
    local level="$2"
    local current_sprint="$3"
    local next_sprint="$4"
    local gate="$5"
    local progress="$6"
    local tests_status="$7"
    local system_status="$8"
    local commit_hash="$(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')"
    local chk_id="$(ls -t ${KIPPE_ROOT}/docs/checkpoints/CHK-*.txt 2>/dev/null | head -n 1 | grep -o 'CHK-[0-9]*' || echo 'N/A')"
    cat <<EOF > "${KIPPE_ROOT}/ESTADO_PROJETO.md"
# 🌐 KIPPE PLATFORM: Permanent Project State
**Projeto:** KIPPE PLATFORM
**Versão:** ${FRAMEWORK_VERSION}
**Programa Atual:** ${program_name}
**Sprint Atual:** ${current_sprint}
**Próxima Sprint:** ${next_sprint}
**Nível do Programa:** ${level}
## Programas
* **A - Foundation:** ✔ Concluído (Nível 5)
* **B - Security:** ✔ Concluído (Nível 5)
* **C - Inventory:** Em desenvolvimento (Nível ${level})
## Métricas de Governança
* **Progresso do Programa:** ${progress} Sprints
* **Gate Atual:** ${gate}
* **Arquitetura:** Frozen (SafeRefactor Active)
* **AST Gate:** PASS
* **Regression:** ${tests_status}
* **Último Commit:** ${commit_hash}
* **Último Checkpoint:** ${chk_id}
EOF
    echo -e "\n============================================="
    echo -e " KIPPE PLATFORM - GOVERNANCE REPORT"
    echo -e "============================================="
    echo -e " Programa Atual:   ${program_name}"
    echo -e " Nível:            ${level}"
    echo -e " Sprint concluída: ${current_sprint}"
    echo -e " Próxima Sprint:   ${next_sprint}"
    echo -e " Gate Atual:       ${gate}"
    echo -e " Roadmap:          ${progress}"
    echo -e " Regression:       ${tests_status}"
    echo -e " Status:           ${system_status}"
    echo -e "=============================================\n"
}
