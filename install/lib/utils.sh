#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# Institutional Installation Framework
# ------------------------------------------------------------
# Module  : utils.sh
# Version : 1.0.0
# Status  : Stable
# ============================================================

[[ -n "${KIPPE_UTILS_LOADED:-}" ]] && return 0 2>/dev/null || true
readonly KIPPE_UTILS_LOADED=1

kippe::timestamp() {

    date '+%Y-%m-%d %H:%M:%S'

}

kippe::iso_timestamp() {

    date '+%Y-%m-%dT%H:%M:%S%z'

}

kippe::uuid() {

    if command -v uuidgen >/dev/null 2>&1; then
        uuidgen
    else
        printf "%s-%s\n" \
            "$(date +%s)" \
            "$RANDOM"
    fi

}

kippe::trim() {

    local value="$*"

    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"

    printf "%s" "${value}"

}

kippe::repeat() {

    local char="$1"
    local count="$2"

    printf "%${count}s" "" | tr ' ' "${char}"

}

kippe::separator() {

    kippe::repeat "=" 70
    printf "\n"

}

kippe::pause() {

    read -r -p "Press ENTER to continue..."

}

kippe::yes_no() {

    local answer

    read -r -p "$1 [y/N]: " answer

    case "${answer}" in
        y|Y|yes|YES)
            return 0
            ;;
        *)
            return 1
            ;;
    esac

}

kippe::current_user() {

    whoami

}

kippe::hostname() {

    hostname

}

kippe::platform() {

    uname -s

}

kippe::architecture() {

    uname -m

}

kippe::environment_info() {

cat <<EOF
============================================================
ENVIRONMENT
============================================================

User         : $(kippe::current_user)
Host         : $(kippe::hostname)
Platform     : $(kippe::platform)
Architecture : $(kippe::architecture)
Framework    : ${KIPPE_FRAMEWORK_VERSION:-Unknown}
Repository   : ${KIPPE_ROOT:-Unknown}
Timestamp    : $(kippe::timestamp)

============================================================
EOF

}
