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
    received_quantity: int = 0

    def __post_init__(self):
        if not self.sku or not str(self.sku).strip():
            raise ValueError("SKU é obrigatório na linha do pedido.")
        if self.quantity <= 0:
            raise ValueError("A quantidade do item deve ser estritamente positiva.")
        gross_total = self.unit_price.amount * self.quantity
        if self.discount.amount > gross_total:
            raise ValueError("Desconto não pode exceder o valor bruto da linha.")

    @property
    def subtotal(self) -> MonetaryValue:
        gross_total = self.unit_price.amount * self.quantity
        net_amount = (gross_total - self.discount.amount) + self.tax.amount
        return MonetaryValue(amount=net_amount, currency=self.unit_price.currency)

    def receive(self, qty: int) -> None:
        if self.received_quantity + qty > self.quantity:
            raise ValueError("Quantidade recebida excede o saldo pendente da linha de compra.")
        self.received_quantity += qty

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
            
        valid_statuses = [
            "DRAFT", "SUBMITTED", "UNDER_APPROVAL", "APPROVED", 
            "ORDERED", "PARTIALLY_RECEIVED", "RECEIVED", "CLOSED", "REJECTED", "CANCELLED"
        ]
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
        if self.status in ["APPROVED", "ORDERED", "PARTIALLY_RECEIVED", "RECEIVED", "CLOSED", "CANCELLED"]:
            raise ValueError(f"Operação rejeitada: Não é possível modificar itens em estado {self.status}.")
            
        line = PurchaseOrderLine(
            sku=sku, 
            quantity=quantity, 
            unit_price=MonetaryValue(unit_price),
            discount=MonetaryValue(discount),
            tax=MonetaryValue(tax)
        )
        self.items.append(line)

    def submit(self) -> None:
        if self.status != "DRAFT":
            raise ValueError("Transição inválida: Apenas pedidos em DRAFT podem ser submetidos.")
        if not self.items:
            raise ValueError("Invariante violada: Não é possível submeter um pedido sem itens.")
        self.status = "SUBMITTED"

    def start_approval(self) -> None:
        if self.status != "SUBMITTED":
            raise ValueError("Transição inválida: Pedido precisa estar em SUBMITTED para entrar em aprovação.")
        self.status = "UNDER_APPROVAL"

    def approve(self) -> None:
        if self.status != "UNDER_APPROVAL":
            raise ValueError("Transição inválida: Apenas pedidos em UNDER_APPROVAL podem ser aprovados.")
        self.status = "APPROVED"

    def reject(self) -> None:
        if self.status != "UNDER_APPROVAL":
            raise ValueError("Transição inválida: Apenas pedidos em UNDER_APPROVAL podem ser rejeitados.")
        self.status = "REJECTED"

    def send_to_draft(self) -> None:
        if self.status != "REJECTED":
            raise ValueError("Transição inválida: Apenas pedidos em REJECTED podem retornar para DRAFT.")
        self.status = "DRAFT"

    def place_order(self) -> None:
        if self.status != "APPROVED":
            raise ValueError("Transição inválida: O pedido precisa estar APPROVED para ser transmitido (ORDERED).")
        if not self.supplier_id:
            raise ValueError("Impedir ORDERED sem fornecedor.")
        self.status = "ORDERED"

    def receive_item(self, sku: str, quantity: int) -> None:
        """Transição Data-Driven: Atualiza status baseado no volume físico recebido"""
        if self.status not in ["ORDERED", "PARTIALLY_RECEIVED"]:
            raise ValueError("Transição inválida: Impedir recebimento antes de ORDERED ou após finalizado.")
            
        line = next((item for item in self.items if item.sku == sku), None)
        if not line:
            raise ValueError(f"O SKU {sku} não pertence a este pedido.")
            
        line.receive(quantity)
        
        all_received = all(item.received_quantity == item.quantity for item in self.items)
        self.status = "RECEIVED" if all_received else "PARTIALLY_RECEIVED"

    def close(self) -> None:
        if self.status != "RECEIVED":
            raise ValueError("Apenas pedidos totalmente recebidos podem ser fechados.")
        self.status = "CLOSED"

    def cancel(self) -> None:
        if self.status in ["PARTIALLY_RECEIVED", "RECEIVED", "CLOSED"]:
            raise ValueError("Transição inválida: Pedidos com recebimento físico iniciado não podem ser cancelados.")
        self.status = "CANCELLED"
