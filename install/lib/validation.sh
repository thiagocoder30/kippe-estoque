#!/usr/bin/env bash
# KIPPE PLATFORM PREFLIGHT VALIDATION MODULE
# Prevents malformed scripts from altering the repository state

kippe::validate_script_syntax() {
    local script_path="$1"
    echo "  -> Auditing script bash syntax: ${script_path}"
    if ! bash -n "${script_path}"; then
        kippe::error "Syntax audit FAILED for ${script_path}. Heredoc anomaly or missing EOF detected."
        exit 1
    fi
    echo "  -> Script syntax audit: PASSED"
}
