#!/usr/bin/env bash
# KIPPE PLATFORM TESTING MODULE
# Orchestrates automated validation to prevent regressions.

kippe::test_environment() {
    echo "  -> Validating test dependencies..."
    if ! command -v python &> /dev/null; then
        kippe::error "Python environment not found. Halting."
        exit 1
    fi
    if ! python -m pytest --version &> /dev/null; then
        kippe::error "Pytest not found. Halting."
        exit 1
    fi
}

kippe::test_run_core() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local test_log="${KIPPE_LOG_DIR}/test-core-${timestamp}.log"
    
    echo "  -> Running Core Domain Test Suite..."
    
    if [[ -d "${KIPPE_ROOT}/tests" ]]; then
        if ! python -m pytest "${KIPPE_ROOT}/tests/" -v > "${test_log}" 2>&1; then
            cat "${test_log}"
            kippe::error "Core Domain Tests FAILED. Architecture violation detected. Halting pipeline."
            # FIX: O exit 1 garante que o CI/CD pare IMEDIATAMENTE e não commite lixo.
            exit 1
        fi
        echo "  -> Core Domain Tests PASSED. Log saved to reports/logs."
    else
        echo "  -> No tests/ directory found yet. Skipping validation."
    fi
}

kippe::test_execute_all() {
    echo "[TEST SUITE INITIATED]"
    kippe::test_environment
    kippe::test_run_core
    echo "[TEST SUITE COMPLETED SUCCESSFULLY]"
}
