#!/usr/bin/env bash
# KIPPE PLATFORM PREFLIGHT VALIDATION MODULE
# Prevents malformed scripts and invalid syntax trees from altering the repository state
kippe::validate_script_syntax() {
    local script_path="$1"
    
    echo "  -> Auditing bash syntax: ${script_path}"
    if ! bash -n "${script_path}"; then
        kippe::error "Bash Syntax audit FAILED for ${script_path}. Heredoc anomaly detected."
        exit 1
    fi
    
    echo "  -> Auditing Python AST (Abstract Syntax Tree)..."
    if ! python3 -m compileall -q "${KIPPE_ROOT}/src/" "${KIPPE_ROOT}/app.py" "${KIPPE_ROOT}/tests/"; then
        kippe::error "Python Compile audit FAILED. Syntax, Indentation or Import error detected."
        exit 1
    fi
    
    echo "  -> Preflight Quality Gate: PASSED"
}
