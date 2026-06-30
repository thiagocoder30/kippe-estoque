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
