#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# Institutional Installation Framework
# ------------------------------------------------------------
# Module  : bootstrap.sh
# Version : 1.0.0
# Status  : Stable
# ============================================================

set -Eeuo pipefail

if [[ -n "${KIPPE_BOOTSTRAP_LOADED:-}" ]]; then
    return 0 2>/dev/null || exit 0
fi

readonly KIPPE_BOOTSTRAP_LOADED=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}"

FRAMEWORK_VERSION="1.0.0"

readonly FRAMEWORK_VERSION
readonly LIB_DIR

load_module() {
    local module="$1"

    if [[ ! -f "${LIB_DIR}/${module}" ]]; then
        echo "[KIPPE] ERROR: Missing module: ${module}" >&2
        exit 1
    fi

    # shellcheck source=/dev/null
    source "${LIB_DIR}/${module}"
}

load_module terminal.sh
load_module logger.sh
load_module filesystem.sh
load_module validation.sh
load_module git.sh
load_module markdown.sh
load_module checkpoint.sh
load_module manifest.sh
load_module export.sh
load_module utils.sh
load_module common.sh
load_module banner.sh

kippe::init() {

    export KIPPE_FRAMEWORK_VERSION="${FRAMEWORK_VERSION}"

    export KIPPE_ROOT="$(
        git rev-parse --show-toplevel 2>/dev/null \
        || pwd
    )"

    export KIPPE_INSTALL="${KIPPE_ROOT}/install"

    export KIPPE_LIB="${KIPPE_INSTALL}/lib"

    export KIPPE_LOG_DIR="/sdcard/Download/KIPPE/logs"

    export KIPPE_REPORT_DIR="/sdcard/Download/KIPPE/reports"

    export KIPPE_EXPORT_DIR="/sdcard/Download/KIPPE/exports"

    export KIPPE_CHECKPOINT_DIR="/sdcard/Download/KIPPE/checkpoints"

    mkdir -p \
        "${KIPPE_LOG_DIR}" \
        "${KIPPE_REPORT_DIR}" \
        "${KIPPE_EXPORT_DIR}" \
        "${KIPPE_CHECKPOINT_DIR}"

    kippe::logger_init

    kippe::log INFO "Framework ${FRAMEWORK_VERSION} initialized"

}

kippe::framework_version() {

    echo "${FRAMEWORK_VERSION}"

}
source "${KIPPE_ROOT}/install/lib/testing.sh"
