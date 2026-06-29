from dataclasses import dataclass, field
from datetime import datetime
from typing import List

@dataclass(frozen=True)
class MonetaryValue:
    amount: float
    currency: str = "BRL"

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Valores monetários não podem ser negativos.")
        # Arredonda para 2 casas decimais na criação para garantir consistência financeira
        object.__setattr__(self, 'amount', round(self.amount, 2))

    def __add__(self, other: 'MonetaryValue') -> 'MonetaryValue':
        if self.currency != other.currency:
            raise ValueError("Não é possível somar valores de moedas diferentes.")
        return MonetaryValue(self.amount + other.amount, self.currency)
        
    def __sub__(self, other: 'MonetaryValue') -> 'MonetaryValue':
        if self.currency != other.currency:
            raise ValueError("Não é possível subtrair valores de moedas diferentes.")
        if self.amount < other.amount:
            raise ValueError("Resultado da subtração resultaria em valor negativo.")
        return MonetaryValue(self.amount - other.amount, self.currency)


@dataclass
class PurchaseOrderLine:
    sku: str
    quantity: int
    unit_price: MonetaryValue
    discount: MonetaryValue = field(default_factory=lambda: MonetaryValue(0.0))
    tax: MonetaryValue = field(default_factory=lambda: MonetaryValue(0.0))

    def __post_init__(self):
        if not self.sku or not str(self.sku).strip():
            raise ValueError("SKU é obrigatório na linha do pedido.")
        if self.quantity <= 0:
            raise ValueError("A quantidade do item deve ser estritamente positiva.")
        
        # Invariante financeira: O desconto não pode ser maior que o subtotal bruto
        gross_total = self.unit_price.amount * self.quantity
        if self.discount.amount > gross_total:
            raise ValueError("Desconto não pode exceder o valor bruto da linha.")

    @property
    def subtotal(self) -> MonetaryValue:
        gross_total = self.unit_price.amount * self.quantity
        net_amount = (gross_total - self.discount.amount) + self.tax.amount
        return MonetaryValue(amount=net_amount, currency=self.unit_price.currency)


@dataclass
class PurchaseOrder:
    id: str
    supplier_id: str
    issue_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    status: str = "DRAFT"
    items: List[PurchaseOrderLine] = field(default_factory=list)

    def __post_init__(self):
        if not self.id or not str(self.id).strip():
            raise ValueError("O ID do pedido é obrigatório.")
        if not self.supplier_id or not str(self.supplier_id).strip():
            raise ValueError("O fornecedor (supplier_id) é obrigatório.")
            
        valid_statuses = ["DRAFT", "OPEN", "APPROVED", "PARTIALLY_RECEIVED", "RECEIVED", "CANCELLED"]
        if self.status not in valid_statuses:
            raise ValueError(f"Status inválido. Permitidos: {valid_statuses}")

    @property
    def total_value(self) -> MonetaryValue:
        if not self.items:
            return MonetaryValue(0.0)
            
        currency = self.items[0].unit_price.currency
        total_amount = sum(item.subtotal.amount for item in self.items)
        return MonetaryValue(amount=total_amount, currency=currency)

    def add_item(self, sku: str, quantity: int, unit_price: float, discount: float = 0.0, tax: float = 0.0) -> None:
        if self.status not in ["DRAFT", "OPEN"]:
            raise ValueError(f"Operação rejeitada: Não é possível modificar itens em estado {self.status}.")
            
        if self.items and self.items[0].unit_price.currency != "BRL":
             pass

        line = PurchaseOrderLine(
            sku=sku, 
            quantity=quantity, 
            unit_price=MonetaryValue(unit_price),
            discount=MonetaryValue(discount),
            tax=MonetaryValue(tax)
        )
        self.items.append(line)

    def approve(self) -> None:
        if self.status not in ["DRAFT", "OPEN"]:
            raise ValueError(f"Transição inválida: Apenas pedidos em DRAFT ou OPEN podem ser aprovados.")
        if not self.items:
            raise ValueError("Invariante violada: Não é possível aprovar um pedido sem itens.")
        self.status = "APPROVED"

    def cancel(self) -> None:
        if self.status in ["RECEIVED", "PARTIALLY_RECEIVED"]:
            raise ValueError("Transição inválida: Pedidos com recebimento físico iniciado não podem ser cancelados.")
        self.status = "CANCELLED"

    def reopen(self) -> None:
        if self.status == "CANCELLED":
            raise ValueError("Transição inválida: Um pedido CANCELLED está selado e não pode voltar para OPEN.")
        if self.status not in ["DRAFT", "APPROVED"]:
            raise ValueError(f"Transição inválida a partir do estado {self.status}.")
        self.status = "OPEN"
