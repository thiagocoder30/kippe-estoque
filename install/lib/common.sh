#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# Institutional Installation Framework
# ------------------------------------------------------------
# Module  : common.sh
# Version : 1.0.0
# Status  : Stable
# ============================================================

[[ -n "${KIPPE_COMMON_LOADED:-}" ]] && return 0 2>/dev/null || true
readonly KIPPE_COMMON_LOADED=1

kippe::on_error() {

    local line="${1:-unknown}"

    if declare -F kippe::error >/dev/null; then
        kippe::error "Execution failed at line ${line}"
    else
        echo "[ERROR] Execution failed at line ${line}" >&2
    fi

    exit 1
}

kippe::require_command() {

    local cmd="$1"

    if ! command -v "${cmd}" >/dev/null 2>&1; then
        kippe::error "Required command not found: ${cmd}"
        exit 1
    fi
}

kippe::require_file() {

    local file="$1"

    [[ -f "${file}" ]] || {
        kippe::error "File not found: ${file}"
        exit 1
    }
}

kippe::require_directory() {

    local dir="$1"

    [[ -d "${dir}" ]] || {
        kippe::error "Directory not found: ${dir}"
        exit 1
    }
}

kippe::mkdir() {

    mkdir -p "$1"
}

kippe::timestamp() {

    date +"%Y-%m-%d %H:%M:%S"
}

kippe::step() {

    local current="$1"
    local total="$2"
    local message="$3"

    printf "[%02d/%02d] %s\n" "${current}" "${total}" "${message}"
}

kippe::header() {

    echo
    echo "============================================================"
    echo "KIPPE PLATFORM"
    echo "$1"
    echo "============================================================"
    echo
}

kippe::footer() {

    echo
    echo "============================================================"
    echo "SPRINT FINISHED"
    echo "============================================================"
    echo
}

kippe::framework_info() {

    cat <<EOF
Framework Version : ${KIPPE_FRAMEWORK_VERSION:-unknown}
Repository        : ${KIPPE_ROOT:-unknown}
Timestamp         : $(kippe::timestamp)
EOF
}

kippe::init_environment() {

    trap 'kippe::on_error ${LINENO}' ERR

    kippe::require_command git
    kippe::require_command mkdir
    kippe::require_command cp
    kippe::require_command rm

    export KIPPE_DATE="$(kippe::timestamp)"
}

kippe::success() {

    if declare -F kippe::success_msg >/dev/null; then
        kippe::success_msg "$1"
    else
        echo "[SUCCESS] $1"
    fi
}

kippe::warning() {

    if declare -F kippe::warn >/dev/null; then
        kippe::warn "$1"
    else
        echo "[WARNING] $1"
    fi
}

kippe::fail() {

    kippe::error "$1"
    exit 1
}
