#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E011: APPLICATION QUERY LAYER (FACADE)
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

TOTAL_STEPS=3
kippe::banner_program "E" "E011" "Application Query Layer (Facade)"

# Preparação de Diretórios
mkdir -p "${KIPPE_ROOT}/src/application/warehouse"
mkdir -p "${KIPPE_ROOT}/tests/application/warehouse"
touch "${KIPPE_ROOT}/src/application/warehouse/__init__.py"
touch "${KIPPE_ROOT}/tests/application/warehouse/__init__.py"

kippe::step 1 ${TOTAL_STEPS} "Deploying Inventory Product View (DTO) and Query Service..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/application/warehouse/query_service.py"
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.domain.warehouse import (
    DualStockView, SmartSheetBuilder, ReplenishmentEngine, 
    TrustScoreEngine, OperationalTruthEngine, DivergenceEvent
)
from src.security.exceptions import NotFoundException

@dataclass(frozen=True)
class InventoryProductView:
    """
    Data Transfer Object (DTO) - O Contrato Público da Plataforma.
    Qualquer interface (CLI, Web, App) consumirá exclusivamente este objeto.
    """
    sku: str
    available_total: int
    depot_balance: int
    store_balance: int
    active_batch: Optional[str]
    primary_supplier: Optional[str]
    last_receipt_date: Optional[str]
    first_expiration_date: Optional[str]
    min_stock: int
    ideal_stock: int
    replenishment_needed: bool
    suggested_quantity: int
    trust_score_percentage: int
    divergence_count: int
    last_divergence: Optional[str]
    operational_risk: float
    recommended_action: str
    action_priority: str

class InventoryQueryService:
    """
    Application Service (Façade).
    Orquestra as dezenas de motores de domínio para montar a visão única do SKU.
    """
    def __init__(self, ledger_repo: InventoryAccountRepository):
        self.ledger_repo = ledger_repo

    def get_sku_view(self, sku: str, min_stock: int = 40, ideal_stock: int = 120) -> InventoryProductView:
        # 1. Recupera o Ledger (Fonte da Verdade)
        account = self.ledger_repo.get_by_sku(sku)
        if not account:
            raise NotFoundException(f"SKU {sku} não possui histórico no Ledger.")

        # 2. Reconstrói a Smart Sheet Base (E005)
        sheet = SmartSheetBuilder.build(account, min_stock=min_stock)
        
        # 3. Reconstrói o Estoque Dual (E008)
        # Nota: O account.entries contém toda a fita de eventos (Movement + Receiving)
        dual_stock = DualStockView.calculate(account.entries, sku)
        
        # 4. Avalia Reposição (E006)
        replenishment = ReplenishmentEngine.calculate(sheet, min_stock, ideal_stock)
        
        # 5. Avalia Confiabilidade (E007)
        # Filtramos eventos que representam divergências puras a partir do Ledger
        div_events = [
            DivergenceEvent(e.sku, 0, 0, e.quantity, e.metadata.get("div_type", "SYSTEM_ERROR"), e.reason, e.timestamp) 
            for e in account.entries if e.transaction_type.name == "ADJUSTMENT" and "div_type" in e.metadata
        ]
        trust = TrustScoreEngine.calculate(div_events)
        
        # 6. Avalia a Verdade Operacional Final (E010)
        inbound_risk = 0.0 # Simplificação para o Query (puxaríamos do E009 no ledger)
        divergence_penalty = 1.0 - trust.score
        
        insight = OperationalTruthEngine.evaluate(
            sku=sku,
            stock_total=dual_stock["total"],
            divergence_penalty=divergence_penalty,
            trust_score=trust.score,
            inbound_risk=inbound_risk
        )

        # Montagem do DTO
        last_div = div_events[-1] if div_events else None
        last_div_desc = f"{last_div.divergence_type} ({last_div.delta} un)" if last_div else "Nenhuma"

        return InventoryProductView(
            sku=sku,
            available_total=dual_stock["total"],
            depot_balance=dual_stock["depot"],
            store_balance=dual_stock["store"],
            active_batch=sheet.next_to_expire["id"] if sheet.next_to_expire else "N/A",
            primary_supplier=sheet.last_receipt["supplier"] if sheet.last_receipt else "N/A",
            last_receipt_date=sheet.last_receipt["date"] if sheet.last_receipt else "N/A",
            first_expiration_date=sheet.next_to_expire["expiration"] if sheet.next_to_expire else "N/A",
            min_stock=min_stock,
            ideal_stock=ideal_stock,
            replenishment_needed=(replenishment is not None),
            suggested_quantity=replenishment.suggested_quantity if replenishment else 0,
            trust_score_percentage=int(trust.score * 100),
            divergence_count=trust.divergence_count,
            last_divergence=last_div_desc,
            operational_risk=round((1.0 - trust.score) * 0.4 + divergence_penalty * 0.4, 2),
            recommended_action=insight.suggested_action,
            action_priority=insight.priority
        )
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Application Tests & CLI Output Mock..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/application/warehouse/test_inventory_query_service.py"
import pytest
from src.application.warehouse.query_service import InventoryQueryService
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.domain.warehouse.ledger_repository import InventoryAccountRepository

# Mock de Repositório em Memória
class InMemoryLedgerRepo(InventoryAccountRepository):
    def __init__(self):
        self.accounts = {}
    def save(self, account: InventoryAccount) -> None:
        self.accounts[account.sku] = account
    def get_by_sku(self, sku: str) -> InventoryAccount:
        return self.accounts.get(sku)

def build_scenario(repo):
    account = InventoryAccount(sku="789609890001")
    
    # Recebimento (E009 via E008 propagation)
    account.record_transaction("L240621", TransactionType.GOODS_RECEIPT, 148, "DEPOT", "NF-123", 
        {"supplier": "YPE", "expiration_date": "2026-11-15"})
        
    # Movimentação Loja (E008)
    account.record_transaction("L240621", TransactionType.TRANSFER_OUT, -16, "DEPOT", "APP", 
        {"movement_type": "TO_STORE"})
    account.record_transaction("L240621", TransactionType.TRANSFER_IN, 16, "STORE", "APP", 
        {"movement_type": "TO_STORE"})
        
    # Divergência detectada e ajustada (E007)
    account.record_transaction("L240621", TransactionType.ADJUSTMENT, -3, "DEPOT", "AUDIT", 
        {"div_type": "UNREGISTERED_WITHDRAWAL"})
        
    repo.save(account)

def test_inventory_query_service_produces_unified_view():
    repo = InMemoryLedgerRepo()
    build_scenario(repo)
    
    service = InventoryQueryService(repo)
    view = service.get_sku_view("789609890001", min_stock=40, ideal_stock=120)
    
    assert view.sku == "789609890001"
    assert view.available_total == 145 # 148 - 3 perdidos (o estoque loja vs depot no teste simplificado pode variar, o Ledger é rei)
    assert view.depot_balance == 129 # 148 - 16 - 3
    assert view.store_balance == 16
    assert view.active_batch == "L240621"
    assert view.primary_supplier == "YPE"
    assert view.trust_score_percentage < 100 # Caiu por causa da divergência
    assert view.divergence_count == 1
    assert "UNREGISTERED_WITHDRAWAL (-3 un)" in view.last_divergence
    
    # Teste de renderização console (mock visual)
    print("\\n====================================")
    print(f"SKU: {view.sku}")
    print(f"Disponível: {view.available_total} (Depósito: {view.depot_balance} | Loja: {view.store_balance})")
    print(f"Reposição: {'Sim' if view.replenishment_needed else 'Não'} ({view.suggested_quantity} un)")
    print(f"Trust Score: {view.trust_score_percentage}%")
    print(f"Status: {view.action_priority} - {view.recommended_action}")
    print("====================================")
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Application Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "101" "1.5.0-platform" "E011" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.6" \
    "Application Layer" \
    "E011 (Inventory Query Service)" \
    "PROGRAM E APPLICATION CONCLUDED" \
    "11/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Application Query Layer consolidada. O DTO de visão única do SKU está operacional."
exit 0

