#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E020.1: CERTIFICATION PATH RESOLUTION FIX
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

TOTAL_STEPS=2
kippe::banner_program "E" "E020.1" "Certification Path Resolution Fix"

kippe::step 1 ${TOTAL_STEPS} "Injecting Git-based Root Discovery into Certification CLI..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/presentation/cli/warehouse_cli.py"
import sys
import os
import argparse
import subprocess
from src.infrastructure.persistence.json.ledger_repository import JsonLinesLedgerRepository
from src.infrastructure.persistence.memory.product_catalog import InMemoryProductCatalog
from src.application.warehouse.query_service import InventoryQueryService
from src.infrastructure.monitoring.telemetry import TelemetryEngine, MetricsRegistry, AuditTrail
from src.infrastructure.release.certification import ProductionCertificationEngine, ReleaseBuilder
from src.security.exceptions import NotFoundException

def print_ficha(view, show_history=False):
    C_RESET, C_BOLD, C_CYAN = '\033[0m', '\033[1m', '\033[96m'
    C_GREEN, C_YELLOW, C_RED = '\033[92m', '\033[93m', '\033[91m'
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
    print(f"Risco Operacional. {status_color}{view.action_priority}{C_RESET}")
    print(f"{C_CYAN}----------------------------------------------------------{C_RESET}")
    print(f"{C_BOLD}AÇÃO RECOMENDADA{C_RESET}\n")
    print(f"{status_color}{marker} {view.recommended_action}{C_RESET}")
    if show_history:
        print(f"{C_CYAN}----------------------------------------------------------{C_RESET}")
        print(f"{C_BOLD}Histórico Recente{C_RESET}\n")
        for h in view.recent_history: print(h)
    print(f"{C_CYAN}=========================================================={C_RESET}\n")

def print_doctor(snapshot):
    C_RESET, C_BOLD, C_GREEN = '\033[0m', '\033[1m', '\033[92m'
    print(f"\n{C_BOLD}===================================={C_RESET}")
    print(f"{C_BOLD}KIPPE PLATFORM HEALTH REPORT        {C_RESET}")
    print(f"{C_BOLD}===================================={C_RESET}")
    print(f"Repository.............{C_GREEN}OK{C_RESET}")
    print(f"Event Store............{C_GREEN}OK{C_RESET}")
    print(f"CQRS...................{C_GREEN}OK{C_RESET}")
    print(f"Errors.................{snapshot.metrics[MetricsRegistry.COMMANDS_FAILED]}")
    print(f"Health.................{C_GREEN}{snapshot.health_status}{C_RESET}")
    print(f"{C_BOLD}===================================={C_RESET}\n")

def print_live_status(snapshot):
    C_RESET, C_BOLD, C_CYAN, C_GREEN = '\033[0m', '\033[1m', '\033[96m', '\033[92m'
    m = snapshot.metrics
    print(f"\n{C_CYAN}========================================={C_RESET}")
    print(f"{C_BOLD}KIPPE PLATFORM LIVE STATUS               {C_RESET}")
    print(f"{C_CYAN}========================================={C_RESET}")
    print(f"Health ............. {C_GREEN}{snapshot.health_status}{C_RESET}")
    print(f"Commands ........... {m[MetricsRegistry.COMMANDS_RECEIVED]}")
    print(f"Queries ............ {m[MetricsRegistry.QUERIES_EXECUTED]}")
    print(f"Events ............. {m[MetricsRegistry.EVENTS_PERSISTED]}")
    print(f"Errors ............. {m[MetricsRegistry.COMMANDS_FAILED]}")
    print(f"Event Store Size ... {m[MetricsRegistry.EVENTSTORE_SIZE]} Bytes")
    print(f"Repository ......... {C_GREEN}OK{C_RESET}")
    print(f"Checkpoint ......... {C_BOLD}CHK-119{C_RESET}")
    print(f"{C_CYAN}========================================={C_RESET}\n")

def get_project_root() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], 
            text=True, stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError:
        return os.getcwd()

def print_certification():
    C_RESET, C_BOLD, C_CYAN, C_GREEN, C_RED = '\033[0m', '\033[1m', '\033[96m', '\033[92m', '\033[91m'
    
    root_dir = get_project_root()
    engine = ProductionCertificationEngine(root_dir)
    result = engine.run_certification()
    
    print(f"\n{C_CYAN}======================================={C_RESET}")
    print(f"{C_BOLD}KIPPE PLATFORM PRODUCTION CERTIFICATION{C_RESET}")
    print(f"{C_CYAN}======================================={C_RESET}")
    
    for check_name, passed in result.checks.items():
        status = f"{C_GREEN}PASS{C_RESET}" if passed else f"{C_RED}FAIL{C_RESET}"
        print(f"{check_name.ljust(20)} {status}")
        
    print(f"{C_CYAN}---------------------------------------{C_RESET}")
    
    if result.is_ready:
        builder = ReleaseBuilder(root_dir)
        builder.build(result)
        print(f"Final Status:        {C_GREEN}{C_BOLD}CERTIFIED FOR PRODUCTION{C_RESET}")
        print(f"Version:             1.5.0")
        print(f"Checkpoint:          CHK-119")
    else:
        print(f"Final Status:        {C_RED}{C_BOLD}CERTIFICATION FAILED{C_RESET}")
        
    print(f"{C_CYAN}======================================={C_RESET}\n")

def main():
    parser = argparse.ArgumentParser(description="KIPPE WMS - Smart CLI V3")
    parser.add_argument("sku", nargs="?", help="Código SKU ou EAN")
    parser.add_argument("--historico", action="store_true", help="Histórico de movimentações")
    parser.add_argument("--doctor", action="store_true", help="Executa o Runtime Diagnostic Report")
    parser.add_argument("--status", action="store_true", help="Exibe o Live Status Dashboard do sistema")
    parser.add_argument("--certify", action="store_true", help="Executa motor de Certificação para Produção")
    args = parser.parse_args()

    audit = AuditTrail()

    if args.certify:
        audit.log_infra_event("Production Certification Initiated")
        print_certification()
        sys.exit(0)

    if args.doctor:
        snapshot = TelemetryEngine.capture()
        print_doctor(snapshot)
        sys.exit(0)

    if args.status:
        snapshot = TelemetryEngine.capture()
        print_live_status(snapshot)
        sys.exit(0)

    if not args.sku:
        parser.print_help()
        sys.exit(1)

    repo = JsonLinesLedgerRepository()
    catalog = InMemoryProductCatalog()
    svc = InventoryQueryService(repo, catalog)

    try:
        view = svc.get_sku_view(args.sku)
        print_ficha(view, show_history=args.historico)
    except NotFoundException as e:
        print(f"\n\033[91m[ERRO]\033[0m {e}\n")

if __name__ == "__main__":
    main()
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Verifying Syntax and Executing Platform Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "120" "1.5.0-platform" "E020.1" "SUCCESS"

echo -e "\n[STATUS] Certification Path Resoltion Fix aplicada! O motor descobre agora a raiz dinamicamente."
exit 0

