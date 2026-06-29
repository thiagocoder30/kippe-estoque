#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D003: PURCHASE ORDER LINES & MONETARY VALUE OBJECTS
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
kippe::banner_program "D" "D003" "Purchase Order Lines"

kippe::step 1 ${TOTAL_STEPS} "Deploying Monetary Value Objects and PO Lines Entities..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/procurement/order.py"
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
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Complete Test Suite for Purchase Order Lines..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/procurement/test_purchase_order_aggregate.py"
import pytest
from src.domain.procurement.order import PurchaseOrder, PurchaseOrderLine, MonetaryValue

def test_monetary_value_object():
    v1 = MonetaryValue(10.50)
    v2 = MonetaryValue(5.25)
    
    assert v1.amount == 10.50
    assert (v1 + v2).amount == 15.75
    assert (v1 - v2).amount == 5.25
    
    with pytest.raises(ValueError, match="Valores monetários não podem ser negativos"):
        MonetaryValue(-1.0)
        
    with pytest.raises(ValueError, match="resultaria em valor negativo"):
        v2 - v1

def test_purchase_order_line_subtotal():
    line = PurchaseOrderLine(
        sku="SKU-A",
        quantity=10,
        unit_price=MonetaryValue(100.0), # Bruto = 1000
        discount=MonetaryValue(100.0),   # -100
        tax=MonetaryValue(50.0)          # +50
    )
    assert line.subtotal.amount == 950.0

def test_purchase_order_line_discount_invariant():
    with pytest.raises(ValueError, match="Desconto não pode exceder o valor bruto"):
        PurchaseOrderLine(
            sku="SKU-B",
            quantity=1,
            unit_price=MonetaryValue(50.0),
            discount=MonetaryValue(60.0) 
        )

def test_purchase_order_creation_and_derived_total():
    order = PurchaseOrder(id="PO-1001", supplier_id="SUP-001")
    assert order.status == "DRAFT"
    
    order.add_item(sku="SKU-A", quantity=10, unit_price=5.0)
    order.add_item(sku="SKU-B", quantity=2, unit_price=50.0, discount=10.0, tax=5.0)
    
    assert len(order.items) == 2
    assert order.total_value.amount == 145.0

def test_purchase_order_enforces_supplier_and_id():
    with pytest.raises(ValueError, match="ID do pedido é obrigatório"):
        PurchaseOrder(id="", supplier_id="SUP-001")
    with pytest.raises(ValueError, match="fornecedor \\(supplier_id\\) é obrigatório"):
        PurchaseOrder(id="PO-1002", supplier_id="")

def test_approval_state_machine_invariants():
    order = PurchaseOrder(id="PO-1003", supplier_id="SUP-001")
    
    with pytest.raises(ValueError, match="Não é possível aprovar um pedido sem itens"):
        order.approve()
        
    order.add_item(sku="SKU-C", quantity=100, unit_price=1.5)
    order.approve()
    assert order.status == "APPROVED"
    
    with pytest.raises(ValueError, match="Não é possível modificar itens em estado APPROVED"):
        order.add_item(sku="SKU-D", quantity=10, unit_price=2.0)

def test_cancellation_and_reopen_state_machine():
    order = PurchaseOrder(id="PO-1004", supplier_id="SUP-001")
    order.cancel()
    assert order.status == "CANCELLED"
    
    with pytest.raises(ValueError, match="Um pedido CANCELLED está selado"):
        order.reopen()

def test_cannot_cancel_received_orders():
    order = PurchaseOrder(id="PO-1005", supplier_id="SUP-001", status="PARTIALLY_RECEIVED")
    with pytest.raises(ValueError, match="recebimento físico iniciado não podem ser cancelados"):
        order.cancel()
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Contracts (Domain & Value Object Lock)..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado
kippe::checkpoint_create "067" "1.4.0-procurement" "D003" "SUCCESS"

# Sincronização de Governança
kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D003 (Purchase Order Lines)" \
    "D004 — Approval Workflow" \
    "3/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Agregado PurchaseOrder Line e Value Objects monetarios (D003) selados contratualmente."
exit 0

