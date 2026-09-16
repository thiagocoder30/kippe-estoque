from dataclasses import dataclass, field
from typing import List

from src.domain.procurement.order import MonetaryValue


@dataclass
class SupplierInvoiceLine:
    """
    Linha documental da Nota Fiscal do fornecedor.

    O SKU representa a identidade interna do produto quando já houver
    conciliação com o catálogo Kippe. Uma linha fiscal ainda não conciliada
    pode manter sku vazio sem que o domínio fabrique uma identidade interna.
    """

    sku: str
    quantity: int
    unit_price: MonetaryValue
    supplier_product_code: str = ""
    description: str = ""
    gtin: str = ""
    commercial_unit: str = ""

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError(
                "A quantidade faturada deve ser estritamente positiva."
            )


@dataclass
class SupplierInvoice:
    """
    Entidade documental: SupplierInvoice (Nota Fiscal de Entrada).

    Representa a expectativa fiscal recebida do fornecedor e preserva
    identidade suficiente para futura conferência e conciliação.

    SupplierInvoice não possui autoridade para alterar estoque.
    """

    invoice_number: str
    supplier_id: str
    lines: List[SupplierInvoiceLine] = field(default_factory=list)
    access_key: str = ""
    series: str = ""
    origin_document: str = "MANUAL"

    def __post_init__(self):
        if not self.invoice_number or not str(self.invoice_number).strip():
            raise ValueError(
                "O número da Nota Fiscal é obrigatório."
            )

        if not self.supplier_id or not str(self.supplier_id).strip():
            raise ValueError(
                "O ID do fornecedor é obrigatório na Nota Fiscal."
            )

    @property
    def total_value(self) -> MonetaryValue:
        if not self.lines:
            return MonetaryValue(0.0)

        total = sum(
            (
                line.unit_price.amount * line.quantity
                for line in self.lines
            )
        )

        return MonetaryValue(
            amount=total,
            currency=self.lines[0].unit_price.currency,
        )
