#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E013: AUDIT LAYER & OPERATIONAL COMPLIANCE
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

TOTAL_STEPS=4
kippe::banner_program "E" "E013" "Audit Layer & Operational Compliance"

kippe::step 1 ${TOTAL_STEPS} "Deploying Audit Service (Application Layer)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/application/warehouse/audit_service.py"
from dataclasses import dataclass, field
from typing import List, Dict
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.domain.warehouse.ledger import TransactionType
from src.domain.catalog.product import ProductCatalogRepository

@dataclass(frozen=True)
class SkuAuditReport:
    sku: str
    description: str
    total_events: int
    total_adjustments: int
    adjustment_ratio: float
    unregistered_withdrawals: int
    expired_losses: int
    compliance_status: str  # SECURE, WARNING, CRITICAL

@dataclass(frozen=True)
class GlobalAuditReport:
    total_skus_audited: int
    total_system_events: int
    global_health_score: float
    critical_skus: List[SkuAuditReport] = field(default_factory=list)

class InventoryAuditService:
    """
    Application Service dedicado à Auditoria Operacional.
    Varre o Event Store para encontrar padrões de anomalia (excessos de ajustes, perdas).
    """
    def __init__(self, ledger_repo: InventoryAccountRepository, catalog_repo: ProductCatalogRepository):
        self.ledger_repo = ledger_repo
        self.catalog_repo = catalog_repo

    def run_global_audit(self, skus: List[str]) -> GlobalAuditReport:
        total_events = 0
        critical_skus = []
        global_health_points = 0.0

        for sku in skus:
            account = self.ledger_repo.get_by_sku(sku)
            if not account or not account.entries:
                continue

            events = account.entries
            total_evs = len(events)
            total_events += total_evs
            
            adjustments = 0
            unregistered = 0
            expired = 0

            for e in events:
                if e.transaction_type == TransactionType.ADJUSTMENT:
                    adjustments += 1
                    div_type = e.metadata.get("div_type", "")
                    if div_type == "UNREGISTERED_WITHDRAWAL":
                        unregistered += 1
                    elif div_type == "EXPIRED_LOSS":
                        expired += 1

            ratio = (adjustments / total_evs) if total_evs > 0 else 0
            
            if ratio > 0.15 or unregistered > 3:
                status = "CRITICAL"
            elif ratio > 0.05 or unregistered > 0:
                status = "WARNING"
            else:
                status = "SECURE"

            product = self.catalog_repo.get_by_sku(sku)
            desc = product.description if product else "Desconhecido"

            sku_report = SkuAuditReport(
                sku=sku, description=desc, total_events=total_evs,
                total_adjustments=adjustments, adjustment_ratio=round(ratio, 2),
                unregistered_withdrawals=unregistered, expired_losses=expired,
                compliance_status=status
            )

            if status != "SECURE":
                critical_skus.append(sku_report)
            
            # Cálculo simples de saúde: 1.0 é perfeito. Reduz conforme o ratio de problemas.
            global_health_points += (1.0 - ratio)

        avg_health = (global_health_points / len(skus)) if skus else 1.0

        return GlobalAuditReport(
            total_skus_audited=len(skus),
            total_system_events=total_events,
            global_health_score=round(avg_health * 100, 2),
            critical_skus=sorted(critical_skus, key=lambda x: x.adjustment_ratio, reverse=True)
        )
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Integrating Audit Layer into Smart CLI..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/presentation/cli/warehouse_cli.py"
import sys
import argparse
from src.infrastructure.persistence.json.ledger_repository import JsonLinesLedgerRepository
from src.infrastructure.persistence.memory.product_catalog import InMemoryProductCatalog
from src.application.warehouse.query_service import InventoryQueryService
from src.application.warehouse.audit_service import InventoryAuditService
from src.security.exceptions import NotFoundException

def print_ficha(view, show_history=False):
    C_RESET = '\033[0m'
    C_BOLD = '\033[1m'
    C_CYAN = '\033[96m'
    C_GREEN = '\033[92m'
    C_YELLOW = '\033[93m'
    C_RED = '\033[91m'

    status_color = C_GREEN if view.action_priority == "LOW" else (C_RED if view.action_priority in ["CRITICAL", "HIGH"] else C_YELLOW)
    marker = "✓" if view.action_priority == "LOW" else "⚠"
    dte_str = str(view.days_to_expire) if view.days_to_expire is not None else "N/A"

    print(f"\n{C_CYAN}=========================================================={C_RESET}")
    print(f"{C_BOLD}               FICHA OPERACIONAL DO PRODUTO               {C_RESET}")
    print(f"{C_CYAN}=========================================================={C_RESET}")
    print(f"EAN............... {view.sku}")
    print(f"Descrição......... {view.description}")
    print(f"Marca............. {view.brand}")
    print(f"Categoria......... {view.category}\n")
    print(f"Fornecedor........ {view.primary_supplier}")
    print(f"Recebido.......... {view.last_receipt_date[:10] if view.last_receipt_date else 'N/A'}\n")
    print(f"Lote Ativo........ {view.active_batch}")
    print(f"Validade.......... {view.first_expiration_date}")
    print(f"Dias para vencer.. {dte_str}")
    print(f"{C_CYAN}----------------------------------------------------------{C_RESET}")
    print(f"{C_BOLD}ESTOQUE{C_RESET}\n")
    print(f"Depósito.......... {view.depot_balance}")
    print(f"Loja.............. {view.store_balance}")
    print(f"Total............. {C_BOLD}{view.available_total}{C_RESET}\n")
    print(f"{C_CYAN}----------------------------------------------------------{C_RESET}")
    print(f"{C_BOLD}CONFIABILIDADE{C_RESET}\n")
    print(f"Trust Score....... {view.trust_score_percentage}%")
    print(f"Divergências...... {view.divergence_count}")
    print(f"Última............ {view.last_divergence}\n")
    print(f"Risco Operacional. {status_color}{view.action_priority}{C_RESET}")
    print(f"{C_CYAN}----------------------------------------------------------{C_RESET}")
    print(f"{C_BOLD}AÇÃO RECOMENDADA{C_RESET}\n")
    print(f"{status_color}{marker} {view.recommended_action}{C_RESET}")
    
    if show_history:
        print(f"{C_CYAN}----------------------------------------------------------{C_RESET}")
        print(f"{C_BOLD}Histórico Recente{C_RESET}\n")
        for h in view.recent_history:
            print(h)
    print(f"{C_CYAN}=========================================================={C_RESET}\n")

def print_auditoria(report):
    C_RESET = '\033[0m'
    C_BOLD = '\033[1m'
    C_CYAN = '\033[96m'
    C_RED = '\033[91m'
    C_YELLOW = '\033[93m'
    C_GREEN = '\033[92m'

    print(f"\n{C_CYAN}=========================================================={C_RESET}")
    print(f"{C_BOLD}              RELATÓRIO DE AUDITORIA (COMPLIANCE)         {C_RESET}")
    print(f"{C_CYAN}=========================================================={C_RESET}")
    print(f"SKUs Auditados:     {report.total_skus_audited}")
    print(f"Eventos Analisados: {report.total_system_events}")
    
    health_color = C_GREEN if report.global_health_score >= 90 else (C_YELLOW if report.global_health_score >= 70 else C_RED)
    print(f"Saúde Global:       {health_color}{report.global_health_score}%{C_RESET}\n")
    
    if not report.critical_skus:
        print(f"{C_GREEN}✓ Nenhum padrão crítico de anomalia detetado.{C_RESET}")
    else:
        print(f"{C_RED}⚠ SKUs EXIGINDO ATENÇÃO OPERACIONAL:{C_RESET}")
        for sku_rep in report.critical_skus:
            color = C_RED if sku_rep.compliance_status == "CRITICAL" else C_YELLOW
            print(f"\n  {C_BOLD}[{sku_rep.sku}] {sku_rep.description}{C_RESET}")
            print(f"  Status: {color}{sku_rep.compliance_status}{C_RESET} | Taxa Erro: {int(sku_rep.adjustment_ratio*100)}%")
            print(f"  Retiradas Invisíveis: {sku_rep.unregistered_withdrawals}")
    print(f"{C_CYAN}=========================================================={C_RESET}\n")

def main():
    parser = argparse.ArgumentParser(description="KIPPE WMS - Smart CLI V2")
    parser.add_argument("sku", nargs="?", help="Código SKU ou EAN do produto (Opcional se usar flags globais)")
    parser.add_argument("--historico", action="store_true", help="Exibe o histórico recente de movimentações do SKU")
    parser.add_argument("--auditoria", action="store_true", help="Gera relatório global de conformidade operacional")
    args = parser.parse_args()

    repo = JsonLinesLedgerRepository()
    catalog = InMemoryProductCatalog()

    if args.auditoria:
        # Para efeitos de demonstração, auditaremos um conjunto fixo. Num cenário real, o repo lista os SKUs.
        audit_svc = InventoryAuditService(repo, catalog)
        report = audit_svc.run_global_audit(["789609890001", "000000000000"]) 
        print_auditoria(report)
        sys.exit(0)

    if not args.sku:
        parser.print_help()
        sys.exit(1)

    svc = InventoryQueryService(repo, catalog)
    try:
        view = svc.get_sku_view(args.sku)
        print_ficha(view, show_history=args.historico)
    except NotFoundException as e:
        print(f"\n\033[91m[ERRO]\033[0m {e}\n")

if __name__ == "__main__":
    main()
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Deploying Application Tests for Audit Layer..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/application/warehouse/test_audit_service.py"
import pytest
from src.application.warehouse.audit_service import InventoryAuditService
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.infrastructure.persistence.memory.product_catalog import InMemoryProductCatalog

class InMemoryLedgerRepo(InventoryAccountRepository):
    def __init__(self):
        self.accounts = {}
    def save(self, account: InventoryAccount) -> None:
        self.accounts[account.sku] = account
    def get_by_sku(self, sku: str) -> InventoryAccount:
        return self.accounts.get(sku)

def test_inventory_audit_service_detects_critical_skus():
    repo = InMemoryLedgerRepo()
    catalog = InMemoryProductCatalog()
    
    # Simula um SKU altamente problemático
    account = InventoryAccount(sku="789609890001")
    account.record_transaction("L1", TransactionType.GOODS_RECEIPT, 100, "DEPOT", "NF")
    account.record_transaction("L1", TransactionType.ADJUSTMENT, -5, "DEPOT", "AUDIT", {"div_type": "UNREGISTERED_WITHDRAWAL"})
    account.record_transaction("L1", TransactionType.ADJUSTMENT, -2, "DEPOT", "AUDIT", {"div_type": "UNREGISTERED_WITHDRAWAL"})
    repo.save(account)
    
    audit_svc = InventoryAuditService(repo, catalog)
    report = audit_svc.run_global_audit(["789609890001"])
    
    assert report.total_skus_audited == 1
    assert report.total_system_events == 3
    assert len(report.critical_skus) == 1
    
    crit_sku = report.critical_skus[0]
    assert crit_sku.unregistered_withdrawals == 2
    assert crit_sku.total_adjustments == 2
    # 2 ajustes em 3 eventos = ~66% de taxa de erro
    assert crit_sku.compliance_status == "CRITICAL"
KIPPE_HUNK

kippe::step 4 ${TOTAL_STEPS} "Verifying Syntax and Executing Platform Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

kippe::checkpoint_create "108" "1.5.0-platform" "E013" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.8" \
    "Platform Level" \
    "E013 (Audit Layer)" \
    "E014 — Command Pattern" \
    "13/20 Sprints" \
    "ACTIVE"

echo -e "\n[STATUS] Sprint E013 (Audit Layer) Concluída. Plataforma KIPPE agora executa auditorias de compliance!"
exit 0

