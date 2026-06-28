#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# Institutional Installation Framework
# ------------------------------------------------------------
# Module  : filesystem.sh
# Version : 1.0.0
# Status  : Stable
# ============================================================

[[ -n "${KIPPE_FILESYSTEM_LOADED:-}" ]] && return 0 2>/dev/null || true
readonly KIPPE_FILESYSTEM_LOADED=1

kippe::exists() {

    [[ -e "$1" ]]

}

kippe::is_file() {

    [[ -f "$1" ]]

}

kippe::is_directory() {

    [[ -d "$1" ]]

}

kippe::mkdir() {

    mkdir -p "$1"

}

kippe::mkdirs() {

    local dir

    for dir in "$@"; do
        mkdir -p "${dir}"
    done

}

kippe::remove() {

    local target="$1"

    [[ -e "${target}" ]] && rm -rf "${target}"

}

kippe::copy() {

    cp -R "$1" "$2"

}

kippe::move() {

    mv "$1" "$2"

}

kippe::touch() {

    touch "$1"

}

kippe::write_file() {

    local file="$1"

    shift

    mkdir -p "$(dirname "${file}")"

    cat > "${file}" <<EOF
$*
EOF

}

kippe::append_file() {

    local file="$1"

    shift

    cat >> "${file}" <<EOF
$*
EOF

}

kippe::safe_write() {

    local file="$1"

    shift

    if [[ ! -f "${file}" ]]; then

        kippe::write_file "${file}" "$@"

        return

    fi

    kippe::warn "Skipping existing file: ${file}"

}

kippe::create_structure() {

    local root="$1"

    shift

    local dir

    for dir in "$@"; do

        mkdir -p "${root}/${dir}"

    done

}

kippe::list_files() {

    find "$1" -type f | sort

}

kippe::list_directories() {

    find "$1" -type d | sort

}

kippe::count_files() {

    find "$1" -type f | wc -l

}

kippe::count_directories() {

    find "$1" -type d | wc -l

}
