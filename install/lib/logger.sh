#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# Institutional Installation Framework
# ------------------------------------------------------------
# Module  : logger.sh
# Version : 1.0.0
# Status  : Stable
# ============================================================

[[ -n "${KIPPE_LOGGER_LOADED:-}" ]] && return 0 2>/dev/null || true
readonly KIPPE_LOGGER_LOADED=1

KIPPE_LOG_LEVEL="${KIPPE_LOG_LEVEL:-INFO}"
KIPPE_LOG_FILE=""

kippe::logger_init() {

    local log_dir="${KIPPE_LOG_DIR:-/tmp}"

    mkdir -p "${log_dir}"

    KIPPE_LOG_FILE="${log_dir}/$(date +%Y%m%d-%H%M%S).log"

    touch "${KIPPE_LOG_FILE}"
}

kippe::logger_file() {

    echo "${KIPPE_LOG_FILE}"
}

kippe::logger_write() {

    local level="$1"
    shift

    local message="$*"

    local timestamp
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"

    printf "[%s] [%s] %s\n" \
        "${timestamp}" \
        "${level}" \
        "${message}" \
        | tee -a "${KIPPE_LOG_FILE}"
}

kippe::log() {

    local level="$1"
    shift

    kippe::logger_write "${level}" "$*"
}

kippe::debug() {

    [[ "${KIPPE_LOG_LEVEL}" == "DEBUG" ]] || return 0

    kippe::logger_write "DEBUG" "$*"
}

kippe::info() {

    kippe::logger_write "INFO" "$*"
}

kippe::warn() {

    kippe::logger_write "WARN" "$*"
}

kippe::error() {

    kippe::logger_write "ERROR" "$*" >&2
}

kippe::success_msg() {

    kippe::logger_write "SUCCESS" "$*"
}

kippe::separator() {

    printf '%*s\n' 70 '' | tr ' ' '=' | tee -a "${KIPPE_LOG_FILE}"
}

kippe::section() {

    kippe::separator
    kippe::info "$*"
    kippe::separator
}

kippe::start_step() {

    kippe::info "START :: $*"
}

kippe::finish_step() {

    kippe::success_msg "DONE :: $*"
}

kippe::logger_close() {

    kippe::info "Logger finished."
}
