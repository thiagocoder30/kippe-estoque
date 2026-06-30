#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D020.1: FIX SMOKE TEST DOMAIN STATE TRANSITIONS
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

# 1. Carregamento do Framework
source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=2
kippe::banner_program "D" "D020.1" "Fix Smoke Test Domain State Transitions"

kippe::step 1 ${TOTAL_STEPS} "Applying Hotfix to Smoke Test Engine (Strict Domain Enforcement)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/certification/smoke_test.py"
from src.bootstrap import Bootstrap
from src.security.correlation import ExecutionContext
from src.domain.procurement.supplier import Supplier
import traceback
import sys

class SmokeTestEngine:
    """Executa um fluxo vital completo E2E para certificar o runtime respeitando os contratos do Domínio."""
    @staticmethod
    def execute() -> bool:
        try:
            app = Bootstrap(use_memory=True)
            ctx = ExecutionContext(user_id="SMOKE_TESTER")
            
            # 1. Configura Infra
            app.sup_repo.save(Supplier("SUP-SMOKE", "Corp", "001", "a@a.com", "ACTIVE"))
            
            # 2. Executa Use Case (Atravessando Decorator, Validator, Domain, Repo) - Retorna status DRAFT
            create_uc = app.get_create_po_use_case()
            create_uc.execute(ctx, "PO-SMK-01", "SUP-SMOKE", [{"sku": "ITM", "quantity": 10, "unit_price": 100.0}])
            
            # 3. Transição Estrita da Máquina de Estados (DRAFT -> SUBMITTED -> UNDER_APPROVAL)
            # Como a Application Layer não possui casos de uso dedicados para Submit/StartApproval, 
            # simulamos o fluxo de negócio via repositório para o Smoke Test respeitar as invariantes.
            order = app.po_repo.get_by_id("PO-SMK-01")
            order.submit()
            order.start_approval()
            app.po_repo.save(order)
            
            # 4. Executa Aprovação no Use Case
            approve_uc = app.get_approve_po_use_case()
            approve_uc.execute(ctx, "PO-SMK-01")
            
            # 5. Valida Estado Final
            saved = app.po_repo.get_by_id("PO-SMK-01")
            return saved is not None and saved.status == "APPROVED"
            
        except Exception as e:
            print(f"\\n[SMOKE TEST FATAL ERROR] {type(e).__name__}: {e}")
            traceback.print_exc(file=sys.stdout)
            return False
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Platform Self-Test..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"

# Executa regressão e o Self-Test que invocará a nova SmokeTestEngine
echo -e "\n-> Executando Regressão Base..."
kippe::test_execute_all

echo -e "\n-> Executando Certificação de Runtime (Self-Test)..."
python3 "${KIPPE_ROOT}/src/selftest.py"

# Registro de Estado e Manifesto
kippe::checkpoint_create "087" "1.4.0-procurement" "D020.1" "SUCCESS"

kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D020.1 (Smoke Test Fix)" \
    "PROGRAM D CONCLUDED" \
    "20/20 Sprints" \
    "CERTIFIED"

echo -e "\n[STATUS] Smoke Test Domain Transition Fix (D020.1) implantado com sucesso."
exit 0

