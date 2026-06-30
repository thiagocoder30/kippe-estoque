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
