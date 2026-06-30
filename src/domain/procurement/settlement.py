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
