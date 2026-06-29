from dataclasses import dataclass, field
from typing import List
from src.domain.procurement.order import MonetaryValue

@dataclass
class SupplierInvoiceLine:
    """Linha da Nota Fiscal do Fornecedor"""
    sku: str
    quantity: int
    unit_price: MonetaryValue

    def __post_init__(self):
        if not self.sku or not str(self.sku).strip():
            raise ValueError("SKU é obrigatório na linha da nota fiscal.")
        if self.quantity <= 0:
            raise ValueError("A quantidade faturada deve ser estritamente positiva.")

@dataclass
class SupplierInvoice:
    """
    Entidade: SupplierInvoice (Nota Fiscal de Entrada)
    Representa o documento fiscal de cobrança emitido pelo fornecedor.
    """
    invoice_number: str
    supplier_id: str
    lines: List[SupplierInvoiceLine] = field(default_factory=list)

    def __post_init__(self):
        if not self.invoice_number or not str(self.invoice_number).strip():
            raise ValueError("O número da Nota Fiscal é obrigatório.")
        if not self.supplier_id or not str(self.supplier_id).strip():
            raise ValueError("O ID do fornecedor é obrigatório na Nota Fiscal.")

    @property
    def total_value(self) -> MonetaryValue:
        if not self.lines:
            return MonetaryValue(0.0)
        total = sum((line.unit_price.amount * line.quantity) for line in self.lines)
        return MonetaryValue(amount=total, currency=self.lines[0].unit_price.currency)
