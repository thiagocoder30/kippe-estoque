#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D009: INVOICE SETTLEMENT
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

# 1. Carregamento do Framework
source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

# Blindagem de Infraestrutura (Fail-Fast)
for fn in kippe::init kippe::validate_script_syntax kippe::test_execute_all kippe::checkpoint_create; do
    if ! declare -F "$fn" >/dev/null; then
        echo "[FATAL] Framework function missing: $fn. O script foi interrompido."
        exit 1
    fi
done

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=3
kippe::banner_program "D" "D009" "Invoice Settlement & Financial Closure"

kippe::step 1 ${TOTAL_STEPS} "Deploying Settlement Entities and Value Objects..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/procurement/settlement.py"
from dataclasses import dataclass, field
from typing import List
from datetime import datetime
from src.domain.procurement.order import MonetaryValue

@dataclass(frozen=True)
class PaymentTerms:
    """Value Object definindo os prazos e condições de pagamento."""
    description: str
    due_days: int

    def __post_init__(self):
        if self.due_days < 0:
            raise ValueError("O prazo de pagamento não pode ser negativo.")

@dataclass(frozen=True)
class PaymentRecord:
    """Value Object representando uma transação financeira de liquidação."""
    amount: MonetaryValue
    reference: str
    payment_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

@dataclass
class InvoiceSettlement:
    """
    Agregado: InvoiceSettlement (Liquidação de Fatura)
    Gerencia o ciclo de pagamentos e o saldo pendente (Outstanding Balance)
    vinculado a uma Nota Fiscal após o sucesso do Three-Way Match.
    """
    settlement_id: str
    invoice_number: str
    po_id: str
    total_amount: MonetaryValue
    payment_terms: PaymentTerms
    status: str = "PENDING"  # PENDING, PARTIALLY_PAID, PAID
    payments: List[PaymentRecord] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.settlement_id or not self.invoice_number or not self.po_id:
            raise ValueError("IDs de liquidação, nota fiscal e pedido são obrigatórios.")
        
        valid_statuses = ["PENDING", "PARTIALLY_PAID", "PAID"]
        if self.status not in valid_statuses:
            raise ValueError(f"Status de liquidação inválido. Permitidos: {valid_statuses}")
            
    @property
    def paid_amount(self) -> MonetaryValue:
        """Soma total dos pagamentos registrados."""
        total = sum(p.amount.amount for p in self.payments)
        return MonetaryValue(amount=total, currency=self.total_amount.currency)
        
    @property
    def outstanding_balance(self) -> MonetaryValue:
        """Cálculo derivado do saldo devedor."""
        return self.total_amount - self.paid_amount
        
    def register_payment(self, amount: MonetaryValue, reference: str) -> None:
        """Registra um pagamento e atualiza o estado de liquidação."""
        if self.status == "PAID":
            raise ValueError("Liquidação já concluída. Não é possível registrar novos pagamentos.")
            
        if amount.amount <= 0:
            raise ValueError("O valor do pagamento deve ser estritamente positivo.")
            
        if amount.currency != self.total_amount.currency:
            raise ValueError("A moeda do pagamento deve ser a mesma da fatura.")
            
        if amount.amount > self.outstanding_balance.amount:
            raise ValueError(f"Pagamento ({amount.amount}) excede o saldo devedor ({self.outstanding_balance.amount}).")
            
        self.payments.append(PaymentRecord(amount=amount, reference=reference))
        
        # Transição Data-Driven
        if self.outstanding_balance.amount == 0.0:
            self.status = "PAID"
        else:
            self.status = "PARTIALLY_PAID"
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Test Suite for Invoice Settlement..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/procurement/test_invoice_settlement.py"
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
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Regression Suite..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto de Governança
kippe::checkpoint_create "073" "1.4.0-procurement" "D009" "SUCCESS"

kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D009 (Invoice Settlement)" \
    "D010 — Procurement Analytics Extension" \
    "9/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Invoice Settlement Engine (D009) consolidado, mantendo o Procurement autocontido."
exit 0

