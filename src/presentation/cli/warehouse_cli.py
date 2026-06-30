import sys
import argparse
from src.infrastructure.persistence.json.ledger_repository import JsonLinesLedgerRepository
from src.application.warehouse.query_service import InventoryQueryService
from src.security.exceptions import NotFoundException

def print_ficha(view):
    C_RESET = '\033[0m'
    C_BOLD = '\033[1m'
    C_CYAN = '\033[96m'
    C_GREEN = '\033[92m'
    C_YELLOW = '\033[93m'
    C_RED = '\033[91m'

    status_color = C_GREEN if view.action_priority == "LOW" else (C_RED if view.action_priority in ["CRITICAL", "HIGH"] else C_YELLOW)
    status_marker = "✓" if view.action_priority == "LOW" else "⚠"

    print(f"\n{C_CYAN}===================================================={C_RESET}")
    print(f"{C_BOLD} FICHA OPERACIONAL DO SKU: {view.sku}{C_RESET}")
    print(f"{C_CYAN}===================================================={C_RESET}")
    print(f" {C_BOLD}Disponível:{C_RESET} {view.available_total} un")
    print(f" {C_BOLD}Depósito:{C_RESET}   {view.depot_balance} un   |   {C_BOLD}Loja:{C_RESET} {view.store_balance} un")
    print(f"{C_CYAN}----------------------------------------------------{C_RESET}")
    print(f" {C_BOLD}Fornecedor:{C_RESET} {view.primary_supplier}")
    print(f" {C_BOLD}Lote Ativo:{C_RESET} {view.active_batch}")
    print(f" {C_BOLD}Recebido:{C_RESET}   {view.last_receipt_date[:10] if view.last_receipt_date else 'N/A'}")
    print(f" {C_BOLD}Validade:{C_RESET}   {view.first_expiration_date}")
    print(f"{C_CYAN}----------------------------------------------------{C_RESET}")
    print(f" {C_BOLD}Reposição:{C_RESET}  {'SIM' if view.replenishment_needed else 'NÃO'} (Sugestão: {view.suggested_quantity} un)")
    print(f" {C_BOLD}TrustScore:{C_RESET} {view.trust_score_percentage}%")
    print(f" {C_BOLD}Divergência:{C_RESET}{view.divergence_count} registada(s)")
    print(f" {C_BOLD}Última Div:{C_RESET} {view.last_divergence}")
    print(f"{C_CYAN}----------------------------------------------------{C_RESET}")
    print(f" {C_BOLD}STATUS:{C_RESET}     {status_color}{status_marker} {view.action_priority}{C_RESET}")
    print(f" {C_BOLD}AÇÃO:{C_RESET}       {status_color}{view.recommended_action}{C_RESET}")
    print(f"{C_CYAN}===================================================={C_RESET}\n")

def main():
    parser = argparse.ArgumentParser(description="KIPPE WMS - Smart CLI")
    parser.add_argument("sku", help="Código SKU ou EAN do produto")
    args = parser.parse_args()

    repo = JsonLinesLedgerRepository()
    svc = InventoryQueryService(repo)

    try:
        view = svc.get_sku_view(args.sku)
        print_ficha(view)
    except NotFoundException as e:
        print(f"\n\033[91m[ERRO]\033[0m {e}\n")

if __name__ == "__main__":
    main()
