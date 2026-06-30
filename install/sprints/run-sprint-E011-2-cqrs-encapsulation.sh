#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E011.2: CQRS ENCAPSULATION & LEDGER PARSING
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
kippe::banner_program "E" "E011.2" "CQRS Encapsulation & Ledger Parsing"

kippe::step 1 ${TOTAL_STEPS} "Encapsulating Ledger Parsing inside DivergenceEngine (Domain)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/divergence.py"
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, List, Any

DivergenceType = Literal[
    "THEFT_SUSPECTED",
    "UNREGISTERED_WITHDRAWAL",
    "PHYSICAL_COUNT_CORRECTION",
    "SYSTEM_ERROR",
    "EXPIRED_LOSS"
]

@dataclass(frozen=True)
class DivergenceEvent:
    sku: str
    system_quantity: int
    physical_quantity: int
    delta: int
    divergence_type: DivergenceType
    reason: Optional[str]
    created_at: str

@dataclass(frozen=True)
class TrustScore:
    sku: str
    score: float
    divergence_count: int
    total_adjustment_volume: int
    risk_level: str

@dataclass(frozen=True)
class InventoryRealitySnapshot:
    sku: str
    system_quantity: int
    physical_quantity: int
    divergence: int
    trust_score: float
    last_updated: str

class DivergenceEngine:
    @staticmethod
    def evaluate(sku: str, system_quantity: int, physical_quantity: int, reason: Optional[str] = None) -> Optional[DivergenceEvent]:
        delta = physical_quantity - system_quantity
        if delta == 0:
            return None

        divergence_type = DivergenceEngine._classify(delta, reason)
        return DivergenceEvent(
            sku=sku, system_quantity=system_quantity, physical_quantity=physical_quantity,
            delta=delta, divergence_type=divergence_type, reason=reason,
            created_at=datetime.now().isoformat()
        )

    @staticmethod
    def _classify(delta: int, reason: Optional[str]) -> DivergenceType:
        if reason and "venc" in reason.lower(): return "EXPIRED_LOSS"
        if delta < 0: return "UNREGISTERED_WITHDRAWAL"
        if delta > 0: return "PHYSICAL_COUNT_CORRECTION"
        return "SYSTEM_ERROR"

    @staticmethod
    def extract_from_ledger(entries: List[Any]) -> List[DivergenceEvent]:
        """
        Fábrica de Reconstrução: Lê a Fonte da Verdade (Ledger) e materializa os eventos de divergência.
        Blinda a Camada de Aplicação contra os detalhes estruturais do Ledger.
        """
        events = []
        for e in entries:
            if e.transaction_type.name == "ADJUSTMENT" and "div_type" in e.metadata:
                events.append(DivergenceEvent(
                    sku=e.sku,
                    system_quantity=0,
                    physical_quantity=0,
                    delta=e.quantity,
                    divergence_type=e.metadata.get("div_type", "SYSTEM_ERROR"),
                    reason=e.metadata.get("reason"),
                    created_at=e.timestamp
                ))
        return events

class TrustScoreEngine:
    @staticmethod
    def calculate(events: List[DivergenceEvent]) -> TrustScore:
        if not events:
            return TrustScore(sku="UNKNOWN", score=1.0, divergence_count=0, total_adjustment_volume=0, risk_level="LOW")

        total_delta = sum(abs(e.delta) for e in events)
        count = len(events)
        score = 1.0 - min(0.5, count * 0.05) - min(0.5, total_delta * 0.01)
        score = max(0.0, score)

        if score >= 0.8: risk = "LOW"
        elif score >= 0.5: risk = "MEDIUM"
        elif score >= 0.2: risk = "HIGH"
        else: risk = "CRITICAL"

        return TrustScore(sku=events[0].sku, score=round(score, 2), divergence_count=count, total_adjustment_volume=total_delta, risk_level=risk)

class InventoryRealityEngine:
    @staticmethod
    def build_snapshot(sku: str, system_qty: int, physical_qty: int, trust_score: float) -> InventoryRealitySnapshot:
        return InventoryRealitySnapshot(sku=sku, system_quantity=system_qty, physical_quantity=physical_qty,
            divergence=physical_qty - system_qty, trust_score=trust_score, last_updated=datetime.now().isoformat())
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Cleaning Application Service (Orchestrator Role Only)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/application/warehouse/query_service.py"
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.domain.warehouse import (
    DualStockView, SmartSheetBuilder, ReplenishmentEngine, 
    TrustScoreEngine, OperationalTruthEngine, DivergenceEngine
)
from src.security.exceptions import NotFoundException

@dataclass(frozen=True)
class InventoryProductView:
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
    def __init__(self, ledger_repo: InventoryAccountRepository):
        self.ledger_repo = ledger_repo

    def get_sku_view(self, sku: str, min_stock: int = 40, ideal_stock: int = 120) -> InventoryProductView:
        account = self.ledger_repo.get_by_sku(sku)
        if not account:
            raise NotFoundException(f"SKU {sku} não possui histórico no Ledger.")

        sheet = SmartSheetBuilder.build(account, min_stock=min_stock)
        dual_stock = DualStockView.calculate(account.entries, sku)
        replenishment = ReplenishmentEngine.calculate(sheet, min_stock, ideal_stock)
        
        # O Domínio agora reconstrói a sua própria realidade
        div_events = DivergenceEngine.extract_from_ledger(account.entries)
        trust = TrustScoreEngine.calculate(div_events)
        
        insight = OperationalTruthEngine.evaluate(
            sku=sku,
            stock_total=dual_stock["total"],
            divergence_penalty=(1.0 - trust.score),
            trust_score=trust.score,
            inbound_risk=0.0
        )

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
            operational_risk=round((1.0 - trust.score) * 0.4 + (1.0 - trust.score) * 0.4, 2),
            recommended_action=insight.suggested_action,
            action_priority=insight.priority
        )
KIPPE_HUNK

# Ajuste do teste para passar o "reason" corretamente e validar o encapsulamento
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/application/warehouse/test_inventory_query_service.py"
import pytest
from src.application.warehouse.query_service import InventoryQueryService
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.domain.warehouse.ledger_repository import InventoryAccountRepository

class InMemoryLedgerRepo(InventoryAccountRepository):
    def __init__(self):
        self.accounts = {}
    def save(self, account: InventoryAccount) -> None:
        self.accounts[account.sku] = account
    def get_by_sku(self, sku: str) -> InventoryAccount:
        return self.accounts.get(sku)

def build_scenario(repo):
    account = InventoryAccount(sku="789609890001")
    account.record_transaction("L240621", TransactionType.GOODS_RECEIPT, 148, "DEPOT", "NF-123", 
        {"supplier": "YPE", "expiration_date": "2026-11-15"})
    account.record_transaction("L240621", TransactionType.TRANSFER_OUT, -16, "DEPOT", "APP", 
        {"movement_type": "TO_STORE"})
    account.record_transaction("L240621", TransactionType.TRANSFER_IN, 16, "STORE", "APP", 
        {"movement_type": "TO_STORE"})
        
    # Injetando Reason corretamente no metadata
    account.record_transaction("L240621", TransactionType.ADJUSTMENT, -3, "DEPOT", "AUDIT", 
        {"div_type": "UNREGISTERED_WITHDRAWAL", "reason": "Retirada não registrada"})
        
    repo.save(account)

def test_inventory_query_service_produces_unified_view():
    repo = InMemoryLedgerRepo()
    build_scenario(repo)
    
    service = InventoryQueryService(repo)
    view = service.get_sku_view("789609890001", min_stock=40, ideal_stock=120)
    
    assert view.sku == "789609890001"
    assert view.available_total == 145
    assert view.depot_balance == 129
    assert view.store_balance == 16
    assert view.trust_score_percentage < 100
    assert view.divergence_count == 1
    assert "UNREGISTERED_WITHDRAWAL (-3 un)" in view.last_divergence
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Platform Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "103" "1.5.0-platform" "E011.2" "SUCCESS"

echo -e "\n[STATUS] CQRS Encapsulation aplicada. O Domínio reconstrói a sua própria realidade."
exit 0

