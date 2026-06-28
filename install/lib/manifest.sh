#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# Institutional Installation Framework
# ------------------------------------------------------------
# Module  : manifest.sh
# Version : 1.0.0
# Status  : Stable
# ============================================================

[[ -n "${KIPPE_MANIFEST_LOADED:-}" ]] && return 0 2>/dev/null || true
readonly KIPPE_MANIFEST_LOADED=1

kippe::manifest_directory() {

    echo "${KIPPE_ROOT}/reports"

}

kippe::manifest_file() {

    local sprint="$1"

    printf "%s/SPRINT_MANIFEST_%s.json" \
        "$(kippe::manifest_directory)" \
        "${sprint}"

}

kippe::manifest_create() {

    local sprint="$1"
    local program="$2"
    local version="$3"
    local status="$4"
    local next="$5"

    local file

    file="$(kippe::manifest_file "${sprint}")"

    mkdir -p "$(dirname "${file}")"

    cat > "${file}" <<EOF
{
  "platform": "KIPPE PLATFORM",
  "framework_version": "${KIPPE_FRAMEWORK_VERSION:-1.0.0}",
  "program": "${program}",
  "sprint": "${sprint}",
  "version": "${version}",
  "status": "${status}",
  "repository": "$(basename "${KIPPE_ROOT}")",
  "branch": "$(git branch --show-current 2>/dev/null || echo unknown)",
  "commit": "$(git rev-parse --short HEAD 2>/dev/null || echo unknown)",
  "generated_at": "$(date '+%Y-%m-%dT%H:%M:%S%z')",
  "next_sprint": "${next}"
}
EOF

    kippe::success "Manifest created: ${file}"

}

kippe::manifest_exists() {

    [[ -f "$(kippe::manifest_file "$1")" ]]

}

kippe::manifest_show() {

    local sprint="$1"

    cat "$(kippe::manifest_file "${sprint}")"

}

kippe::manifest_info() {

    cat <<EOF
Manifest Directory : $(kippe::manifest_directory)
Framework Version  : ${KIPPE_FRAMEWORK_VERSION:-1.0.0}
EOF

}
