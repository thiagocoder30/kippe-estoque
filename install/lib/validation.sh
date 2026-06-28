#!/usr/bin/env bash
# KIPPE PLATFORM PREFLIGHT VALIDATION MODULE

kippe::validate_script_syntax() {
    local script_path="$1"
    
    echo "  -> Auditing bash syntax: ${script_path}"
    if ! bash -n "${script_path}"; then
        kippe::error "Bash Syntax audit FAILED."
        exit 1
    fi
    
    export PYTHONPATH="${KIPPE_ROOT}"
    if ! python3 "${KIPPE_ROOT}/install/lib/semantic_validator.py"; then
        kippe::error "Semantic Validator FAILED. Mutações perigosas detectadas."
        exit 1
    fi
    
    echo "  -> Auditing Python AST (Abstract Syntax Tree) via compileall..."
    if ! python3 -m compileall -q "${KIPPE_ROOT}/src/" "${KIPPE_ROOT}/app.py" "${KIPPE_ROOT}/tests/"; then
        kippe::error "Python Compile audit FAILED."
        exit 1
    fi
    
    echo "  -> Preflight Quality Gates: PASSED"
}
