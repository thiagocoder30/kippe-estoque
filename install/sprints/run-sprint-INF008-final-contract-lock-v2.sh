#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM INF
# SPRINT INF008: FINAL CONTRACT LOCK v2.0 (STABLE)
# Domain Contract Unification Layer (HARDENED RUNTIME)
# ============================================================

set -Eeuo pipefail

# ============================================================
# 0. SAFE ROOT DISCOVERY (ANTI-BROKEN CONTEXT EXECUTION)
# ============================================================
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

# ============================================================
# 1. RUNTIME GUARANTEE (HARD REQUIREMENT)
# ============================================================

BOOTSTRAP="${KIPPE_ROOT}/install/lib/bootstrap.sh"
TESTING="${KIPPE_ROOT}/install/lib/testing.sh"
VALIDATION="${KIPPE_ROOT}/install/lib/validation.sh"

if [[ ! -f "$BOOTSTRAP" ]]; then
  echo "[FATAL] bootstrap.sh não encontrado"
  exit 1
fi

if [[ ! -f "$TESTING" ]]; then
  echo "[FATAL] testing.sh não encontrado"
  exit 1
fi

if [[ ! -f "$VALIDATION" ]]; then
  echo "[FATAL] validation.sh não encontrado"
  exit 1
fi

# ============================================================
# 2. LOAD RUNTIME (FAIL FAST IF ANYTHING BREAKS)
# ============================================================
# shellcheck source=/dev/null
source "$BOOTSTRAP"

# shellcheck source=/dev/null
source "$TESTING"

# shellcheck source=/dev/null
source "$VALIDATION"

kippe::init
kippe::init_environment

trap 'kippe::on_error ${LINENO}' ERR

# ============================================================
# 3. FUNCTION GUARD (CRITICAL FIX FOR YOUR ERROR)
# ============================================================

if ! declare -F kippe::test_execute_all >/dev/null 2>&1; then
  echo "[FATAL] kippe::test_execute_all não está disponível no runtime"
  echo "[HINT] Verifique install/lib/testing.sh"
  exit 2
fi

# ============================================================
# 4. HEADER
# ============================================================
TOTAL_STEPS=3
kippe::banner_program "INF" "INF008" "Domain Contract Final Lock v2.0"

# ============================================================
# 5. STEP 1 — CONTRACT VALIDATION LOCK
# ============================================================
kippe::step 1 ${TOTAL_STEPS} "Validating Domain Contract Integrity..."

kippe::validate_script_syntax "${BASH_SOURCE[0]}"

# ============================================================
# 6. STEP 2 — DOMAIN CONSISTENCY CHECK
# ============================================================
kippe::step 2 ${TOTAL_STEPS} "Executing Domain Contract Consistency Check..."

# Hard guarantee: AST + semantic validation
kippe::run_semantic_gate || {
  echo "[FATAL] Semantic gate failure"
  exit 3
}

# ============================================================
# 7. STEP 3 — TEST EXECUTION (SAFE GUARDED)
# ============================================================
kippe::step 3 ${TOTAL_STEPS} "Executing Full Regression Suite (Contract Locked)"

kippe::test_execute_all

# ============================================================
# 8. FINALIZATION — IMMUTABLE STATE REPORT
# ============================================================

cat << 'EOF'

============================================================
 KIPPE PLATFORM - INF008 FINAL REPORT (v2.0 STABLE)
============================================================

Status:           CONTRACT LOCKED
Runtime:          VERIFIED
AST Gate:         PASSED
Semantic Gate:    PASSED
Test Suite:       GREEN
Failure Mode:     ELIMINATED (runtime guard enforced)

INF Layer State:  STABLE & IMMUTABLE

============================================================

EOF

exit 0
