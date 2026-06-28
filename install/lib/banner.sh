#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# Institutional Installation Framework
# ------------------------------------------------------------
# Module  : banner.sh
# Version : 1.0.0
# Status  : Stable
# ============================================================

[[ -n "${KIPPE_BANNER_LOADED:-}" ]] && return 0 2>/dev/null || true
readonly KIPPE_BANNER_LOADED=1

kippe::banner() {

    local title="${1:-Institutional Installation Framework}"
    local subtitle="${2:-}"

    kippe::hr

    printf "KIPPE PLATFORM\n"

    printf "Framework Version : %s\n" \
        "${KIPPE_FRAMEWORK_VERSION:-1.0.0}"

    printf "Repository        : %s\n" \
        "${KIPPE_ROOT:-Unknown}"

    printf "Date              : %s\n" \
        "$(date '+%Y-%m-%d %H:%M:%S')"

    kippe::hr

    printf "%s\n" "${title}"

    [[ -n "${subtitle}" ]] && printf "%s\n" "${subtitle}"

    kippe::hr
}

kippe::banner_program() {

    local program="$1"
    local sprint="$2"
    local description="$3"

    kippe::banner \
        "PROGRAM ${program}" \
        "SPRINT ${sprint} - ${description}"
}

kippe::banner_finish() {

    kippe::hr

    printf "SPRINT COMPLETED SUCCESSFULLY\n"

    kippe::hr
}

kippe::banner_error() {

    kippe::hr

    printf "SPRINT FAILED\n"

    kippe::hr
}

kippe::framework_info() {

    cat <<EOF
Framework : ${KIPPE_FRAMEWORK_VERSION:-1.0.0}
Repository: ${KIPPE_ROOT:-Unknown}
Log File  : ${KIPPE_LOG_FILE:-Unavailable}
EOF
}
