#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# Institutional Installation Framework
# ------------------------------------------------------------
# Module  : markdown.sh
# Version : 1.0.0
# Status  : Stable
# ============================================================

[[ -n "${KIPPE_MARKDOWN_LOADED:-}" ]] && return 0 2>/dev/null || true
readonly KIPPE_MARKDOWN_LOADED=1

kippe::md_h1() {

    printf "# %s\n\n" "$1"

}

kippe::md_h2() {

    printf "## %s\n\n" "$1"

}

kippe::md_h3() {

    printf "### %s\n\n" "$1"

}

kippe::md_text() {

    printf "%s\n\n" "$*"

}

kippe::md_bold() {

    printf "**%s**" "$1"

}

kippe::md_italic() {

    printf "*%s*" "$1"

}

kippe::md_code() {

    printf "\`%s\`" "$1"

}

kippe::md_quote() {

    printf "> %s\n\n" "$*"

}

kippe::md_hr() {

    printf "\n---\n\n"

}

kippe::md_list() {

    local item

    for item in "$@"; do
        printf "- %s\n" "${item}"
    done

    printf "\n"

}

kippe::md_numbered_list() {

    local index=1
    local item

    for item in "$@"; do
        printf "%d. %s\n" "${index}" "${item}"
        ((index++))
    done

    printf "\n"

}

kippe::md_table_header() {

    local col

    for col in "$@"; do
        printf "| %s " "${col}"
    done

    printf "|\n"

    for col in "$@"; do
        printf "|---"
    done

    printf "|\n"

}

kippe::md_table_row() {

    local col

    for col in "$@"; do
        printf "| %s " "${col}"
    done

    printf "|\n"

}

kippe::md_code_block() {

    local language="$1"

    shift

    printf "```%s\n" "${language}"
    printf "%s\n" "$*"
    printf "```\n\n"

}

kippe::md_append() {

    local file="$1"

    shift

    {
        printf "%s\n" "$*"
    } >> "${file}"

}

kippe::md_write() {

    local file="$1"

    shift

    mkdir -p "$(dirname "${file}")"

    cat > "${file}" <<EOF
$*
EOF

}
