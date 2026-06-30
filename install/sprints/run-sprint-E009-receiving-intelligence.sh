#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E009: RECEIVING INTELLIGENCE ENGINE (INBOUND TRUTH)
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
kippe::banner_program "E" "E009" "Receiving Intelligence Engine"

kippe::step 1 ${TOTAL_STEPS} "Deploying Inbound Truth Layer (Domain Models)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/receiving.py"
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from src.security.exceptions import BusinessRuleViolation
from src.domain.warehouse.movement import MovementEngine, MovementEvent

@dataclass(frozen=True)
class ReceivingEvent:
    """O evento original de entrada no sistema."""
    sku: str
    supplier: str
    quantity: int
    batch_code: str
    expiration_date: Optional[str]
    invoice_id: Optional[str]
    origin_document: str  # ex: MANUAL, OCR, XML
    created_at: str

@dataclass(frozen=True)
class EvaluatedBatch:
    """O Lote transformado em entidade de risco e rastreabilidade."""
    sku: str
    batch_code: str
    supplier: str
    quantity: int
    expiration_date: str
    received_at: str
    risk_score: float  # 0.0 (Altamente duvidoso) a 1.0 (Auditoria perfeita)

class BatchIntelligenceEngine:
    """Classifica a confiabilidade do lote no momento do nascimento (Recebimento)."""
    @staticmethod
    def evaluate(event: ReceivingEvent) -> EvaluatedBatch:
        risk = 1.0

        # Penalidades por omissão ou fragilidade operacional
        if not event.expiration_date:
            risk -= 0.3
        if not event.invoice_id:
            risk -= 0.2
        if event.origin_document == "MANUAL":
            risk -= 0.1

        risk = max(0.0, min(1.0, risk))

        return EvaluatedBatch(
            sku=event.sku,
            batch_code=event.batch_code,
            supplier=event.supplier,
            quantity=event.quantity,
            expiration_date=event.expiration_date or "UNKNOWN",
            received_at=event.created_at,
            risk_score=round(risk, 2)
        )

class ReceivingEngine:
    """
    Orquestrador Inbound: Regista a entrada, avalia o risco do lote
    e dispara automaticamente o MovementEvent para injetar a verdade no fluxo de stock.
    """
    @staticmethod
    def execute(sku: str, supplier: str, quantity: int, batch_code: str,
                expiration_date: Optional[str] = None, invoice_id: Optional[str] = None,
                origin_document: str = "MANUAL", destination: str = "DEPOT") -> tuple[ReceivingEvent, EvaluatedBatch, MovementEvent]:
        
        if quantity <= 0:
            raise BusinessRuleViolation("Recebimento deve ter quantidade estritamente positiva.")

        # 1. Registo Factual
        receiving_event = ReceivingEvent(
            sku=sku, supplier=supplier, quantity=quantity, batch_code=batch_code,
            expiration_date=expiration_date, invoice_id=invoice_id,
            origin_document=origin_document, created_at=datetime.now().isoformat()
        )

        # 2. Avaliação de Confiança (Risco na Origem)
        evaluated_batch = BatchIntelligenceEngine.evaluate(receiving_event)

        # 3. Propagação para o Micro-Registry (E008 integration)
        movement_event = MovementEngine.register(
            sku=sku,
            quantity=quantity,
            movement_type="RETURN_TO_STOCK", # Incrementa logicamente a view de DEPOT do E008
            origin=f"RECEIVING_{origin_document}",
            destination=destination,
            reason=f"Batch {batch_code} from {supplier}"
        )

        return receiving_event, evaluated_batch, movement_event
KIPPE_HUNK

# Atualiza a API pública
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/__init__.py"
from .topology import Warehouse, StorageLocation
from .ledger import InventoryAccount, LedgerEntry, TransactionType
from .balance import BalanceEngine, BalanceProjection
from .smart_sheet import SkuSmartSheet, SmartSheetBuilder
from .replenishment import ReplenishmentEngine, ReplenishmentSuggestion
from .divergence import DivergenceEvent, TrustScore, InventoryRealitySnapshot, DivergenceEngine, TrustScoreEngine, InventoryRealityEngine
from .movement import MovementEvent, MovementType, DualStockView, MovementEngine
from .receiving import ReceivingEvent, EvaluatedBatch, BatchIntelligenceEngine, ReceivingEngine

__all__ = [
    "Warehouse", "StorageLocation", "InventoryAccount", "LedgerEntry", 
    "TransactionType", "BalanceEngine", "BalanceProjection",
    "SkuSmartSheet", "SmartSheetBuilder",
    "ReplenishmentEngine", "ReplenishmentSuggestion",
    "DivergenceEvent", "TrustScore", "InventoryRealitySnapshot", 
    "DivergenceEngine", "TrustScoreEngine", "InventoryRealityEngine",
    "MovementEvent", "MovementType", "DualStockView", "MovementEngine",
    "ReceivingEvent", "EvaluatedBatch", "BatchIntelligenceEngine", "ReceivingEngine"
]
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Test Suite for Inbound Truth Engine..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/domain/warehouse/test_receiving_intelligence.py"
import pytest
from src.domain.warehouse.receiving import ReceivingEngine, BatchIntelligenceEngine, ReceivingEvent
from src.security.exceptions import BusinessRuleViolation

def test_batch_intelligence_penalizes_poor_inbound_data():
    # 1. Lote Perfeito (XML/OCR, NF, Validade)
    perfect_event = ReceivingEvent("SKU-1", "SUPP-A", 100, "B01", "2026-12-31", "NF-123", "XML_OCR", "2026-07-01T10:00:00")
    perfect_batch = BatchIntelligenceEngine.evaluate(perfect_event)
    assert perfect_batch.risk_score == 1.0

    # 2. Lote Cego (Manual, Sem NF, Sem Validade)
    blind_event = ReceivingEvent("SKU-1", "SUPP-A", 100, "B02", None, None, "MANUAL", "2026-07-01T10:00:00")
    blind_batch = BatchIntelligenceEngine.evaluate(blind_event)
    # Penalidades: -0.3 (validade) -0.2 (NF) -0.1 (manual) = 0.4
    assert blind_batch.risk_score == 0.4

def test_receiving_engine_orchestrates_full_inbound_cycle():
    rec_event, batch, mov_event = ReceivingEngine.execute(
        sku="DETERGENTE",
        supplier="Ype",
        quantity=50,
        batch_code="LOT-XYZ",
        invoice_id="NF-777",
        origin_document="MANUAL", # Forçando Trust 0.9 (perde 0.1 pelo manual)
        expiration_date="2027-01-01"
    )

    # Verifica Evento Factual
    assert rec_event.quantity == 50
    assert rec_event.supplier == "Ype"
    
    # Verifica Qualidade
    assert batch.risk_score == 0.90 
    
    # Verifica Propagação pro Fluxo (E008)
    assert mov_event.sku == "DETERGENTE"
    assert mov_event.quantity == 50
    assert mov_event.origin == "RECEIVING_MANUAL"

def test_receiving_engine_blocks_negative_receipts():
    with pytest.raises(BusinessRuleViolation, match="estritamente positiva"):
        ReceivingEngine.execute("SKU-1", "S", -10, "B1")
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Domain Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "099" "1.5.0-platform" "E009" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.4" \
    "Supply Intelligence & Inbound" \
    "E009 (Receiving Intelligence Engine)" \
    "E010 — Platform Final Verification" \
    "9/20 Sprints" \
    "ACTIVE"

echo -e "\n[STATUS] Receiving Intelligence Engine selado. KIPPE agora mede a confiabilidade da mercadoria na raiz."
exit 0

