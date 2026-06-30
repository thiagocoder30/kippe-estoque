#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E005: SKU SMART SHEET (CQRS READ MODEL)
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
kippe::banner_program "E" "E005" "SKU Smart Sheet (CQRS Projection)"

kippe::step 1 ${TOTAL_STEPS} "Evolving Ledger to Support Operational Metadata..."

# Atualização retrocompatível do Ledger para suportar metadados (Validade, Fornecedor, OCR)
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/ledger.py"
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any
from src.security.exceptions import BusinessRuleViolation

class TransactionType(Enum):
    GOODS_RECEIPT = "GOODS_RECEIPT"
    SALE = "SALE"
    TRANSFER_OUT = "TRANSFER_OUT"
    TRANSFER_IN = "TRANSFER_IN"
    ADJUSTMENT = "ADJUSTMENT"
    CYCLE_COUNT = "CYCLE_COUNT"

@dataclass(frozen=True)
class LedgerEntry:
    id: str
    timestamp: str
    sku: str
    batch_id: str
    transaction_type: TransactionType
    quantity: int
    location_id: str
    reference_document: str
    metadata: Dict[str, Any] = field(default_factory=dict) # Suporte a Validade, Fornecedor, OCR

@dataclass
class InventoryAccount:
    sku: str
    entries: List[LedgerEntry] = field(default_factory=list)

    def record_transaction(self, batch_id: str, tx_type: TransactionType, quantity: int, location_id: str, reference_document: str, metadata: dict = None) -> LedgerEntry:
        if quantity == 0:
            raise BusinessRuleViolation("A quantidade de uma transação no Ledger não pode ser zero.")
            
        if tx_type in [TransactionType.SALE, TransactionType.TRANSFER_OUT] and quantity > 0:
            raise BusinessRuleViolation(f"Transações do tipo {tx_type.value} exigem quantidades negativas.")
            
        if tx_type in [TransactionType.GOODS_RECEIPT, TransactionType.TRANSFER_IN] and quantity < 0:
            raise BusinessRuleViolation(f"Transações do tipo {tx_type.value} exigem quantidades positivas.")

        entry = LedgerEntry(
            id=uuid.uuid4().hex[:12].upper(),
            timestamp=datetime.now().isoformat(),
            sku=self.sku,
            batch_id=batch_id,
            transaction_type=tx_type,
            quantity=quantity,
            location_id=location_id,
            reference_document=reference_document,
            metadata=metadata or {}
        )
        self.entries.append(entry)
        return entry
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Smart Sheet Projection Engine..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/smart_sheet.py"
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.domain.warehouse.balance import BalanceEngine

@dataclass
class SkuSmartSheet:
    """
    Read Model ultra-otimizado para a operação (Ficha Inteligente).
    Responde a todas as perguntas críticas num único ecrã.
    """
    sku: str
    total_balance: int
    reserved_balance: int
    available_balance: int
    locations: Dict[str, int]
    batches: List[Dict[str, Any]]
    next_to_expire: Optional[Dict[str, Any]]
    last_receipt: Optional[Dict[str, Any]]
    recent_history: List[Dict[str, Any]]
    alerts: List[str]

class SmartSheetBuilder:
    """Projeta a Ficha Inteligente varrendo o Ledger de forma otimizada."""
    @staticmethod
    def build(account: InventoryAccount, reserved_qty: int = 0, min_stock: int = 10) -> SkuSmartSheet:
        # 1. Saldo e Localizações (Reutiliza o BalanceEngine E004)
        projection = BalanceEngine.calculate(account)
        
        # 2. Histórico e Recebimentos
        sorted_entries = sorted(account.entries, key=lambda e: e.timestamp, reverse=True)
        recent_history = [{"date": e.timestamp[:10], "type": e.transaction_type.value, "qty": e.quantity, "loc": e.location_id} for e in sorted_entries[:5]]
        
        last_receipt = None
        for e in sorted_entries:
            if e.transaction_type == TransactionType.GOODS_RECEIPT:
                last_receipt = {
                    "date": e.timestamp[:10],
                    "supplier": e.metadata.get("supplier", "Desconhecido"),
                    "nf": e.reference_document,
                    "qty": e.quantity
                }
                break

        # 3. Lotes e Validades (Motor FEFO Base)
        batch_details = {}
        for e in account.entries:
            if e.batch_id not in batch_details:
                batch_details[e.batch_id] = {"id": e.batch_id, "qty": 0, "expiration": e.metadata.get("expiration_date", "9999-12-31")}
            batch_details[e.batch_id]["qty"] += e.quantity
            # Atualiza validade se foi informada num recebimento posterior
            if "expiration_date" in e.metadata:
                batch_details[e.batch_id]["expiration"] = e.metadata["expiration_date"]

        active_batches = [b for b in batch_details.values() if b["qty"] > 0]
        # Ordenação FEFO (First Expire, First Out)
        active_batches.sort(key=lambda b: b["expiration"])
        
        next_to_expire = active_batches[0] if active_batches else None
        
        # 4. Alertas Inteligentes
        alerts = []
        available = projection.total - reserved_qty
        
        if available < min_stock:
            alerts.append(f"⚠ Saldo disponível ({available}) abaixo do mínimo ({min_stock})")
        if len(active_batches) == 1:
            alerts.append("⚠ Lote único em stock")
        if next_to_expire and next_to_expire["expiration"] != "9999-12-31":
            days_to_expire = (datetime.strptime(next_to_expire["expiration"], "%Y-%m-%d") - datetime.now()).days
            if days_to_expire < 30:
                alerts.append(f"⚠ Lote {next_to_expire['id']} vence em {days_to_expire} dias")

        return SkuSmartSheet(
            sku=account.sku,
            total_balance=projection.total,
            reserved_balance=reserved_qty,
            available_balance=available,
            locations=projection.by_location,
            batches=active_batches,
            next_to_expire=next_to_expire,
            last_receipt=last_receipt,
            recent_history=recent_history,
            alerts=alerts
        )
KIPPE_HUNK

# Atualiza a API pública
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/__init__.py"
from .topology import Warehouse, StorageLocation
from .ledger import InventoryAccount, LedgerEntry, TransactionType
from .balance import BalanceEngine, BalanceProjection
from .smart_sheet import SkuSmartSheet, SmartSheetBuilder

__all__ = [
    "Warehouse", "StorageLocation", "InventoryAccount", "LedgerEntry", 
    "TransactionType", "BalanceEngine", "BalanceProjection",
    "SkuSmartSheet", "SmartSheetBuilder"
]
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Deploying Application Query Layer & Tests..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/domain/warehouse/test_smart_sheet.py"
import pytest
from datetime import datetime, timedelta
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.domain.warehouse.smart_sheet import SmartSheetBuilder

def test_smart_sheet_builds_comprehensive_read_model():
    account = InventoryAccount(sku="DETERGENTE-NEUTRO-500ML")
    
    # Recebimento Antigo
    account.record_transaction("L2406", TransactionType.GOODS_RECEIPT, 40, "EST-F-02", "NF-100", 
        {"supplier": "Distribuidora ABC", "expiration_date": (datetime.now() + timedelta(days=25)).strftime("%Y-%m-%d")})
    
    # Venda
    account.record_transaction("L2406", TransactionType.SALE, -8, "EST-F-02", "PED-01")
    
    # Recebimento Novo
    account.record_transaction("L2407", TransactionType.GOODS_RECEIPT, 56, "FLOOR-LIMPEZA", "NF-200",
        {"supplier": "Indústria Ypê", "expiration_date": (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d")})

    # Projeta a Ficha Inteligente (simulando 8 unidades reservadas e 100 de mínimo para forçar alerta)
    sheet = SmartSheetBuilder.build(account, reserved_qty=8, min_stock=100)
    
    # 1. Saldos
    assert sheet.total_balance == (40 - 8 + 56) # 88
    assert sheet.reserved_balance == 8
    assert sheet.available_balance == 80
    
    # 2. Localizações Lean
    assert sheet.locations["EST-F-02"] == 32
    assert sheet.locations["FLOOR-LIMPEZA"] == 56
    
    # 3. Lotes & FEFO
    assert len(sheet.batches) == 2
    assert sheet.next_to_expire is not None
    assert sheet.next_to_expire["id"] == "L2406" # Vence em 25 dias
    
    # 4. Última Entrada
    assert sheet.last_receipt is not None
    assert sheet.last_receipt["supplier"] == "Indústria Ypê"
    assert sheet.last_receipt["nf"] == "NF-200"
    
    # 5. Alertas
    assert any("abaixo do mínimo" in a for a in sheet.alerts)
    assert any("vence em" in a for a in sheet.alerts)
    
    # 6. Histórico
    assert len(sheet.recent_history) == 3
    assert sheet.recent_history[0]["type"] == "GOODS_RECEIPT" # O mais recente primeiro
KIPPE_HUNK

kippe::step 4 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "095" "1.5.0-platform" "E005" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.3" \
    "Operational Projections" \
    "E005 (SKU Smart Sheet)" \
    "E006 — FEFO & Allocation Engine" \
    "5/20 Sprints" \
    "ACTIVE"

echo -e "\n[STATUS] SKU Smart Sheet (Ficha Inteligente) implantada. Projeção operacional 360 graus ativada."
exit 0

