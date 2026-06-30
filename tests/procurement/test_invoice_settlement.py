import pytest
from src.domain.procurement.order import MonetaryValue
from src.domain.procurement.settlement import InvoiceSettlement, PaymentTerms

def test_invoice_settlement_full_payment():
    terms = PaymentTerms(description="Net 30", due_days=30)
    settlement = InvoiceSettlement(
        settlement_id="SET-001",
        invoice_number="NFE-999",
        po_id="PO-001",
        total_amount=MonetaryValue(1000.0),
        payment_terms=terms
    )
    
    assert settlement.status == "PENDING"
    assert settlement.outstanding_balance.amount == 1000.0
    
    # Pagamento Integral
    settlement.register_payment(MonetaryValue(1000.0), reference="TX-123")
    
    assert settlement.status == "PAID"
    assert settlement.paid_amount.amount == 1000.0
    assert settlement.outstanding_balance.amount == 0.0

def test_invoice_settlement_partial_payments():
    terms = PaymentTerms(description="Net 15", due_days=15)
    settlement = InvoiceSettlement(
        settlement_id="SET-002", invoice_number="NFE-888", po_id="PO-002",
        total_amount=MonetaryValue(500.0), payment_terms=terms
    )
    
    # Primeiro Pagamento Parcial
    settlement.register_payment(MonetaryValue(200.0), reference="TX-001")
    assert settlement.status == "PARTIALLY_PAID"
    assert settlement.outstanding_balance.amount == 300.0
    
    # Segundo Pagamento (Quitação)
    settlement.register_payment(MonetaryValue(300.0), reference="TX-002")
    assert settlement.status == "PAID"
    assert settlement.outstanding_balance.amount == 0.0

def test_invoice_settlement_rejects_overpayment():
    terms = PaymentTerms("Net 10", 10)
    settlement = InvoiceSettlement(
        settlement_id="SET-003", invoice_number="NFE-777", po_id="PO-003",
        total_amount=MonetaryValue(100.0), payment_terms=terms
    )
    
    with pytest.raises(ValueError, match="excede o saldo devedor"):
        settlement.register_payment(MonetaryValue(150.0), reference="TX-OVER")

def test_invoice_settlement_rejects_payment_when_already_paid():
    terms = PaymentTerms("Avista", 0)
    settlement = InvoiceSettlement(
        settlement_id="SET-004", invoice_number="NFE-666", po_id="PO-004",
        total_amount=MonetaryValue(50.0), payment_terms=terms
    )
    
    settlement.register_payment(MonetaryValue(50.0), reference="TX-FULL")
    assert settlement.status == "PAID"
    
    with pytest.raises(ValueError, match="Liquidação já concluída"):
        settlement.register_payment(MonetaryValue(10.0), reference="TX-EXTRA")

def test_invoice_settlement_enforces_required_ids():
    terms = PaymentTerms("30 Dias", 30)
    with pytest.raises(ValueError, match="IDs de liquidação, nota fiscal e pedido são obrigatórios"):
        InvoiceSettlement(settlement_id="", invoice_number="NF-1", po_id="PO-1", total_amount=MonetaryValue(10.0), payment_terms=terms)
