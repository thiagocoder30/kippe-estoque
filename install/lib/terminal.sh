#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# Institutional Installation Framework
# ------------------------------------------------------------
# Module  : terminal.sh
# Version : 1.0.0
# Status  : Stable
# ============================================================

[[ -n "${KIPPE_TERMINAL_LOADED:-}" ]] && return 0 2>/dev/null || true
readonly KIPPE_TERMINAL_LOADED=1

if [[ -t 1 ]]; then
    readonly KIPPE_RESET=$'\033[0m'
    readonly KIPPE_BOLD=$'\033[1m'

    readonly KIPPE_RED=$'\033[31m'
    readonly KIPPE_GREEN=$'\033[32m'
    readonly KIPPE_YELLOW=$'\033[33m'
    readonly KIPPE_BLUE=$'\033[34m'
    readonly KIPPE_MAGENTA=$'\033[35m'
    readonly KIPPE_CYAN=$'\033[36m'
else
    readonly KIPPE_RESET=""
    readonly KIPPE_BOLD=""

    readonly KIPPE_RED=""
    readonly KIPPE_GREEN=""
    readonly KIPPE_YELLOW=""
    readonly KIPPE_BLUE=""
    readonly KIPPE_MAGENTA=""
    readonly KIPPE_CYAN=""
fi

kippe::println() {

    printf "%b\n" "$*"

}

kippe::print() {

    printf "%b" "$*"

}

kippe::title() {

    kippe::println ""
    kippe::println "${KIPPE_BOLD}${KIPPE_CYAN}$*${KIPPE_RESET}"
    kippe::println ""

}

kippe::info_msg() {

    kippe::println "${KIPPE_BLUE}[INFO]${KIPPE_RESET} $*"

}

kippe::success_msg() {

    kippe::println "${KIPPE_GREEN}[ OK ]${KIPPE_RESET} $*"

}

kippe::warn_msg() {

    kippe::println "${KIPPE_YELLOW}[WARN]${KIPPE_RESET} $*"

}

kippe::error_msg() {

    kippe::println "${KIPPE_RED}[FAIL]${KIPPE_RESET} $*" >&2

}

kippe::step_msg() {

    local current="$1"
    local total="$2"
    shift 2

    printf "%b[%02d/%02d]%b %s\n" \
        "${KIPPE_MAGENTA}" \
        "${current}" \
        "${total}" \
        "${KIPPE_RESET}" \
        "$*"

}

kippe::hr() {

    printf '%*s\n' 70 '' | tr ' ' '='

}

kippe::blank() {

    echo

}
