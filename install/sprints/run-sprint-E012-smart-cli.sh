#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E012: SMART CLI & LEDGER PERSISTENCE (PRESENTATION)
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

TOTAL_STEPS=4
kippe::banner_program "E" "E012" "Smart CLI & Ledger Persistence"

# Preparação de Diretórios
mkdir -p "${KIPPE_ROOT}/src/infrastructure/persistence/json"
mkdir -p "${KIPPE_ROOT}/src/presentation/cli"
touch "${KIPPE_ROOT}/src/presentation/cli/__init__.py"

kippe::step 1 ${TOTAL_STEPS} "Deploying JSON Ledger Repository (Infrastructure)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/persistence/json/ledger_repository.py"
import os
import json
import tempfile
from typing import Optional, Dict, Any
from src.domain.warehouse.ledger import InventoryAccount, LedgerEntry, TransactionType
from src.domain.warehouse.ledger_repository import InventoryAccountRepository

class JsonLedgerRepository(InventoryAccountRepository):
    """Persistência atómica do Livro-Razão (Event Store) em JSON."""
    def __init__(self, file_path: str = "data/inventory_ledger.json"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def save(self, account: InventoryAccount) -> None:
        data = self._read_all()
        entries = []
        for e in account.entries:
            entries.append({
                "id": e.id, "timestamp": e.timestamp, "sku": e.sku,
                "batch_id": e.batch_id, "transaction_type": e.transaction_type.name,
                "quantity": e.quantity, "location_id": e.location_id,
                "reference_document": e.reference_document, "metadata": e.metadata
            })
        data[account.sku] = {"sku": account.sku, "entries": entries}
        self._atomic_write(data)

    def get_by_sku(self, sku: str) -> Optional[InventoryAccount]:
        data = self._read_all()
        if sku not in data:
            return None
        raw = data[sku]
        account = InventoryAccount(sku=sku)
        for e in raw["entries"]:
            entry = LedgerEntry(
                id=e["id"], timestamp=e["timestamp"], sku=e["sku"],
                batch_id=e["batch_id"], transaction_type=TransactionType[e["transaction_type"]],
                quantity=e["quantity"], location_id=e["location_id"],
                reference_document=e["reference_document"], metadata=e["metadata"]
            )
            account.entries.append(entry)
        return account

    def _read_all(self) -> Dict[str, Any]:
        if not os.path.exists(self.file_path): return {}
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _atomic_write(self, data: Dict[str, Any]) -> None:
        dir_name = os.path.dirname(self.file_path)
        fd, tmp = tempfile.mkstemp(dir=dir_name, suffix=".json")
        with os.fdopen(fd, 'w', encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.file_path)
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Smart CLI Interface (Presentation Layer)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/presentation/cli/warehouse_cli.py"
import sys
import argparse
from src.infrastructure.persistence.json.ledger_repository import JsonLedgerRepository
from src.application.warehouse.query_service import InventoryQueryService
from src.security.exceptions import NotFoundException

def print_ficha(view):
    # Cores ANSI para UX de terminal
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

    repo = JsonLedgerRepository()
    svc = InventoryQueryService(repo)

    try:
        view = svc.get_sku_view(args.sku)
        print_ficha(view)
    except NotFoundException as e:
        print(f"\n\033[91m[ERRO]\033[0m {e}\n")

if __name__ == "__main__":
    main()
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Generating Seed Data (Mocking a real operation)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/presentation/cli/seed_warehouse.py"
from src.infrastructure.persistence.json.ledger_repository import JsonLedgerRepository
from src.domain.warehouse.ledger import InventoryAccount, TransactionType

def generate_seed():
    repo = JsonLedgerRepository()
    account = InventoryAccount(sku="789609890001")
    
    # Recebimento E009 - Conferente: Thiago
    account.record_transaction("L240621", TransactionType.GOODS_RECEIPT, 148, "DEPOT", "NF-123",
        {"supplier": "YPE", "expiration_date": "2026-11-15", "conferente": "Thiago"})
    
    # Micro-Registry E008 (Reposição para Loja)
    account.record_transaction("L240621", TransactionType.TRANSFER_OUT, -16, "DEPOT", "APP",
        {"movement_type": "TO_STORE"})
    account.record_transaction("L240621", TransactionType.TRANSFER_IN, 16, "STORE", "APP",
        {"movement_type": "TO_STORE"})
    
    # Divergência E007
    account.record_transaction("L240621", TransactionType.ADJUSTMENT, -3, "DEPOT", "AUDIT",
        {"div_type": "UNREGISTERED_WITHDRAWAL", "reason": "Retirada não registada - Analisado pelo Thiago"})
    
    repo.save(account)
    print("✓ Base de Dados do Ledger (Seed) populada com sucesso!")

if __name__ == "__main__":
    generate_seed()
KIPPE_HUNK

kippe::step 4 ${TOTAL_STEPS} "Verifying Syntax and Executing Platform Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Popula o banco de dados e testa o CLI
python3 "${KIPPE_ROOT}/src/presentation/cli/seed_warehouse.py"

# Registro de Estado e Manifesto
kippe::checkpoint_create "104" "1.5.0-platform" "E012" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.7" \
    "Presentation Layer" \
    "E012 (Smart CLI)" \
    "E013 — End-to-End Audit" \
    "12/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Smart CLI (Presentation) e Ledger Persistence consolidados!"
exit 0

