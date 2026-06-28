#!/usr/bin/env bash
set -Eeuo pipefail
kippe::test_execute_all() {
    echo "  -> Executing Core Regression Suite with Unified PYTHONPATH..."
    # Garante de forma irreversível a localização correta dos pacotes de domínio
    export PYTHONPATH="${KIPPE_ROOT}"
    python3 -m pytest -q "${KIPPE_ROOT}/tests/"
}
