#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM F: OPERATIONAL INTELLIGENCE
# SPRINT F001-A: CONTRACT SYNCHRONIZATION
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=3
kippe::banner_program "F" "F001-A" "Contract Synchronization (Repository & Tests)"

kippe::step 1 ${TOTAL_STEPS} "Patching Test Mocks to comply with updated InventoryAccountRepository contract..."

# Script Python para injetar def get_all() dinamicamente em todos os Mocks de teste
python3 -c "
import os, glob, re

pattern = r'( +)def get_by_sku\(.*?\).*?:\n( +)return self\.accounts\.get\(sku\)'
target_dir = os.path.join('${KIPPE_ROOT}', 'tests')

patched_files = 0
for filepath in glob.glob(f'{target_dir}/**/*.py', recursive=True):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'class InMemoryLedgerRepo' in content and 'def get_all' not in content:
        def repl(m):
            indent_def = m.group(1)
            indent_body = m.group(2)
            return f'{m.group(0)}\n{indent_def}def get_all(self):\n{indent_body}return list(self.accounts.values())'
        
        new_content = re.sub(pattern, repl, content)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        patched_files += 1

print(f'\033[92m   ✓ {patched_files} ficheiros de teste atualizados com o método get_all().\033[0m')
"

kippe::step 2 ${TOTAL_STEPS} "Removing unused Catalog Global Dependency from Projection Engine..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/application/warehouse/projections/engine.py"
from datetime import datetime
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.domain.catalog.product import ProductCatalogRepository
from src.application.warehouse.query_service import InventoryQueryService
from src.application.warehouse.projections.models import (
    GlobalInventoryProjection, ExpirationProjection, PurchaseProjection
)

class ProjectionEngine:
    """
    Constrói as Visões Operacionais agregadas numa única varredura.
    Desacopla os Dashboards e Relatórios da necessidade de consultar o Ledger a cada clique.
    """
    def __init__(self, ledger_repo: InventoryAccountRepository, catalog_repo: ProductCatalogRepository):
        self.ledger_repo = ledger_repo
        self.catalog_repo = catalog_repo
        self.query_svc = InventoryQueryService(ledger_repo, catalog_repo)

    def build_all(self):
        accounts = self.ledger_repo.get_all()
        
        # Estruturas de agregação
        total_items = 0
        trust_sum = 0
        critical_skus = []
        
        exp_7, exp_15, exp_30, exp_expired = [], [], [], []
        pur_urgent, pur_planned = [], []

        for account in accounts:
            try:
                # Utiliza o orquestrador já existente de domínio para extrair os indicadores do SKU
                view = self.query_svc.get_sku_view(account.sku)
                
                total_items += view.available_total
                trust_sum += view.trust_score_percentage

                # Coleta para Dashboard Global
                if view.action_priority in ["CRITICAL", "HIGH"]:
                    critical_skus.append({
                        "sku": view.sku,
                        "description": view.description,
                        "priority": view.action_priority,
                        "reason": view.recommended_action
                    })

                # Coleta para Expiration Intelligence
                if view.days_to_expire is not None:
                    exp_item = {"sku": view.sku, "description": view.description, "batch": view.active_batch, "days": view.days_to_expire}
                    if view.days_to_expire < 0:
                        exp_expired.append(exp_item)
                    elif view.days_to_expire <= 7:
                        exp_7.append(exp_item)
                    elif view.days_to_expire <= 15:
                        exp_15.append(exp_item)
                    elif view.days_to_expire <= 30:
                        exp_30.append(exp_item)

                # Coleta para Purchase Intelligence
                if view.replenishment_needed:
                    pur_item = {
                        "sku": view.sku, "description": view.description, 
                        "suggested_qty": view.suggested_quantity, "supplier": view.primary_supplier
                    }
                    if view.action_priority == "CRITICAL":
                        pur_urgent.append(pur_item)
                    else:
                        pur_planned.append(pur_item)

            except Exception:
                continue

        total_skus = len(accounts)
        avg_trust = (trust_sum / total_skus) if total_skus > 0 else 100.0
        estimated_value = total_items * 15.50 # Fixo para MVP
        
        critical_skus.sort(key=lambda x: 0 if x["priority"] == "CRITICAL" else 1)
        
        inv_proj = GlobalInventoryProjection(
            total_skus=total_skus, total_items=total_items, estimated_value=estimated_value,
            critical_skus_count=len(critical_skus), avg_trust_score=round(avg_trust, 1),
            top_critical_skus=critical_skus[:10]
        )
        
        exp_proj = ExpirationProjection(expiring_in_7_days=exp_7, expiring_in_15_days=exp_15, expiring_in_30_days=exp_30, already_expired=exp_expired)
        pur_proj = PurchaseProjection(urgent_replenishment=pur_urgent, planned_replenishment=pur_planned)
        
        return inv_proj, exp_proj, pur_proj
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Platform Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado
kippe::checkpoint_create "502" "5.0.0-projections" "F001-A" "SUCCESS"

echo -e "\n[STATUS] Sprint F001-A Concluída. Contratos de Repositório sincronizados e Suíte de Testes Restaurada!"
exit 0

