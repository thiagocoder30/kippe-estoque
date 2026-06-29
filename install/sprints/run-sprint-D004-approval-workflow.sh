#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D004: APPROVAL WORKFLOW & STATE MACHINE
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
kippe::banner_program "D" "D004" "Approval Workflow"

kippe::step 1 ${TOTAL_STEPS} "Deploying Rigid Approval Workflow for PurchaseOrder..."

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
        # Nunca editar linhas após APPROVED (bloqueia APPROVED, ORDERED, PARTIALLY_RECEIVED, RECEIVED, CLOSED, CANCELLED)
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

    def receive_partially(self) -> None:
        if self.status not in ["ORDERED", "PARTIALLY_RECEIVED"]:
            raise ValueError("Transição inválida: Impedir recebimento antes de ORDERED.")
        self.status = "PARTIALLY_RECEIVED"

    def receive_completely(self) -> None:
        if self.status not in ["ORDERED", "PARTIALLY_RECEIVED"]:
            raise ValueError("Transição inválida: Impedir RECEIVED antes de ORDERED.")
        self.status = "RECEIVED"

    def close(self) -> None:
        if self.status != "RECEIVED":
            raise ValueError("Apenas pedidos totalmente recebidos podem ser fechados.")
        self.status = "CLOSED"

    def cancel(self) -> None:
        if self.status in ["PARTIALLY_RECEIVED", "RECEIVED", "CLOSED"]:
            raise ValueError("Transição inválida: Pedidos com recebimento físico iniciado não podem ser cancelados.")
        self.status = "CANCELLED"
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Complete Test Suite for Approval Workflow..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/procurement/test_purchase_order_aggregate.py"
import pytest
from src.domain.procurement.order import PurchaseOrder, PurchaseOrderLine, MonetaryValue

def test_purchase_order_full_approval_workflow():
    order = PurchaseOrder(id="PO-WF-001", supplier_id="SUP-99")
    
    # Adicionar itens (Permitido em DRAFT)
    order.add_item(sku="SKU-X", quantity=10, unit_price=10.0)
    
    # DRAFT -> SUBMITTED
    order.submit()
    assert order.status == "SUBMITTED"
    
    # SUBMITTED -> UNDER_APPROVAL
    order.start_approval()
    assert order.status == "UNDER_APPROVAL"
    
    # UNDER_APPROVAL -> APPROVED
    order.approve()
    assert order.status == "APPROVED"
    
    # Tentativa de editar itens após aprovação deve falhar
    with pytest.raises(ValueError, match="Não é possível modificar itens em estado APPROVED"):
        order.add_item(sku="SKU-Y", quantity=5, unit_price=10.0)
        
    # APPROVED -> ORDERED
    order.place_order()
    assert order.status == "ORDERED"
    
    # ORDERED -> RECEIVED
    order.receive_completely()
    assert order.status == "RECEIVED"
    
    # NUNCA voltar de RECEIVED para ORDERED
    assert not hasattr(order, "reopen")

def test_purchase_order_rejection_workflow():
    order = PurchaseOrder(id="PO-WF-002", supplier_id="SUP-99")
    order.add_item("SKU-Z", 1, 10.0)
    
    order.submit()
    order.start_approval()
    
    # UNDER_APPROVAL -> REJECTED
    order.reject()
    assert order.status == "REJECTED"
    
    # REJECTED -> DRAFT
    order.send_to_draft()
    assert order.status == "DRAFT"
    
    # Em DRAFT pode voltar a editar
    order.add_item("SKU-W", 2, 5.0)
    assert len(order.items) == 2

def test_approval_workflow_invariants():
    order = PurchaseOrder(id="PO-WF-003", supplier_id="SUP-99")
    
    # Impedir aprovação (submissão) sem linhas
    with pytest.raises(ValueError, match="Não é possível submeter um pedido sem itens"):
        order.submit()
        
    order.add_item("SKU-K", 1, 100.0)
    
    # Impedir ORDERED antes de APPROVED
    with pytest.raises(ValueError, match="O pedido precisa estar APPROVED"):
        order.place_order()
        
    # Impedir RECEIVED antes de ORDERED
    with pytest.raises(ValueError, match="Impedir RECEIVED antes de ORDERED"):
        order.receive_completely()

def test_cannot_cancel_after_receipt_starts():
    order = PurchaseOrder(id="PO-WF-004", supplier_id="SUP-99")
    order.add_item("SKU-A", 1, 10.0)
    order.submit()
    order.start_approval()
    order.approve()
    order.place_order()
    order.receive_partially()
    
    with pytest.raises(ValueError, match="recebimento físico iniciado não podem ser cancelados"):
        order.cancel()
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Contracts (Workflow Lock)..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado
kippe::checkpoint_create "068" "1.4.0-procurement" "D004" "SUCCESS"

# Sincronização de Governança
kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D004 (Approval Workflow)" \
    "D005 — Goods Receipt" \
    "4/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Workflow de Aprovacao e Maquina de Estados Rigida (D004) consolidados."
exit 0

