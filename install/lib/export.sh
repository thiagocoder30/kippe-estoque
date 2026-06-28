#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# Institutional Installation Framework
# ------------------------------------------------------------
# Module  : export.sh
# Version : 1.0.0
# Status  : Stable
# ============================================================

[[ -n "${KIPPE_EXPORT_LOADED:-}" ]] && return 0 2>/dev/null || true
readonly KIPPE_EXPORT_LOADED=1

kippe::export_root() {

    echo "/sdcard/Download/KIPPE"

}

kippe::export_init() {

    local root

    root="$(kippe::export_root)"

    mkdir -p \
        "${root}" \
        "${root}/logs" \
        "${root}/reports" \
        "${root}/exports" \
        "${root}/checkpoints"

}

kippe::export_file() {

    local source="$1"
    local destination="$2"

    [[ -f "${source}" ]] || {
        kippe::warn "File not found: ${source}"
        return 1
    }

    mkdir -p "$(dirname "${destination}")"

    cp -f "${source}" "${destination}"

    kippe::info "Exported: ${destination}"

}

kippe::export_directory() {

    local source="$1"
    local destination="$2"

    [[ -d "${source}" ]] || {
        kippe::warn "Directory not found: ${source}"
        return 1
    }

    mkdir -p "${destination}"

    cp -R "${source}/." "${destination}/"

    kippe::info "Directory exported: ${destination}"

}

kippe::export_logs() {

    [[ -n "${KIPPE_LOG_FILE:-}" ]] || return 0

    kippe::export_file \
        "${KIPPE_LOG_FILE}" \
        "$(kippe::export_root)/logs/$(basename "${KIPPE_LOG_FILE}")"

}

kippe::export_manifest() {

    local sprint="$1"

    local file

    file="$(kippe::manifest_file "${sprint}")"

    kippe::export_file \
        "${file}" \
        "$(kippe::export_root)/reports/$(basename "${file}")"

}

kippe::export_checkpoint() {

    local checkpoint="$1"

    local file

    file="$(kippe::checkpoint_file "${checkpoint}")"

    kippe::export_file \
        "${file}" \
        "$(kippe::export_root)/checkpoints/$(basename "${file}")"

}

kippe::export_summary() {

    cat <<EOF

============================================================
EXPORT SUMMARY
============================================================

Destination:
$(kippe::export_root)

Logs:
$(kippe::export_root)/logs

Reports:
$(kippe::export_root)/reports

Checkpoints:
$(kippe::export_root)/checkpoints

============================================================

EOF

}
