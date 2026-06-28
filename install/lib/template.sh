#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# Institutional Installation Framework
# ------------------------------------------------------------
# Module  : template.sh
# Version : 1.0.0
# Status  : Stable
# ============================================================

[[ -n "${KIPPE_TEMPLATE_LOADED:-}" ]] && return 0 2>/dev/null || true
readonly KIPPE_TEMPLATE_LOADED=1

kippe::template_exists() {

    [[ -f "$1" ]]

}

kippe::template_directory() {

    echo "${KIPPE_ROOT}/install/templates"

}

kippe::template_path() {

    local template="$1"

    echo "$(kippe::template_directory)/${template}"

}

kippe::template_render() {

    local template="$1"
    local destination="$2"

    kippe::validate_file "${template}"

    mkdir -p "$(dirname "${destination}")"

    cp "${template}" "${destination}"
}

kippe::template_render_if_missing() {

    local template="$1"
    local destination="$2"

    if [[ -f "${destination}" ]]; then
        kippe::warn "Skipping existing file: ${destination}"
        return 0
    fi

    kippe::template_render "${template}" "${destination}"
}

kippe::template_install() {

    local name="$1"
    local destination="$2"

    local template

    template="$(kippe::template_path "${name}")"

    kippe::template_render "${template}" "${destination}"
}

kippe::template_install_if_missing() {

    local name="$1"
    local destination="$2"

    local template

    template="$(kippe::template_path "${name}")"

    kippe::template_render_if_missing \
        "${template}" \
        "${destination}"
}

kippe::template_list() {

    find "$(kippe::template_directory)" \
        -maxdepth 1 \
        -type f \
        | sort

}

kippe::template_count() {

    find "$(kippe::template_directory)" \
        -maxdepth 1 \
        -type f \
        | wc -l

}
