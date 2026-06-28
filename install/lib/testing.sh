#!/usr/bin/env bash
# KIPPE PLATFORM TESTING MODULE
kippe::test_execute_all() {
    echo "  -> Executing Core Regression Suite..."
    export PYTHONPATH="${KIPPE_ROOT}"
    if ! python3 -m pytest -q "${KIPPE_ROOT}/tests/"; then
        kippe::error "Regression Suite FAILED. Broken Domain Contracts detected."
        exit 1
    fi
    echo "  -> Regression Suite: 100% PASSED"
}
