#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D002: PURCHASE ORDER AGGREGATE & STATE MACHINE
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
        echo "[FATAL] Framework function missing: $fn."
        exit 1
    fi
done

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=3
kippe::banner_program "D" "D002" "Purchase Order Aggregate & State Machine"

kippe::step 1 ${TOTAL_STEPS} "Deploying Purchase Order Aggregate and State Machine..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/procurement/order.py"
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

@dataclass
class PurchaseOrderItem:
    """Objeto de Valor (Value Object) representando a linha do pedido"""
    sku: str
    quantity: int
    unit_price: float

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("A quantidade do item deve ser estritamente positiva.")
        if self.unit_price < 0:
            raise ValueError("O custo unitário não pode ser negativo.")


@dataclass
class PurchaseOrder:
    """
    Agregado Raiz: PurchaseOrder (Pedido de Compra)
    Possui máquina de estados rigorosa e cálculo derivado de totais.
    """
    id: str
    supplier_id: str
    issue_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    status: str = "DRAFT"
    items: List[PurchaseOrderItem] = field(default_factory=list)

    def __post_init__(self):
        # Invariantes Estruturais
        if not self.id or not str(self.id).strip():
            raise ValueError("O ID do pedido é obrigatório.")
        if not self.supplier_id or not str(self.supplier_id).strip():
            raise ValueError("O fornecedor (supplier_id) é obrigatório.")
            
        valid_statuses = ["DRAFT", "OPEN", "APPROVED", "PARTIALLY_RECEIVED", "RECEIVED", "CANCELLED"]
        if self.status not in valid_statuses:
            raise ValueError(f"Status inválido. Permitidos: {valid_statuses}")

    @property
    def total_value(self) -> float:
        """Cálculo derivado dinâmico do valor total do pedido"""
        return sum(item.quantity * item.unit_price for item in self.items)

    def add_item(self, sku: str, quantity: int, unit_price: float) -> None:
        if self.status not in ["DRAFT", "OPEN"]:
            raise ValueError(f"Operação rejeitada: Não é possível modificar itens em estado {self.status}.")
        self.items.append(PurchaseOrderItem(sku=sku, quantity=quantity, unit_price=unit_price))

    # --- MÁQUINA DE ESTADOS INSTITUCIONAL ---
    
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

kippe::step 2 ${TOTAL_STEPS} "Deploying State Machine Test Suite (Contract-First)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/procurement/test_purchase_order_aggregate.py"
import pytest
from src.domain.procurement.order import PurchaseOrder, PurchaseOrderItem

def test_purchase_order_creation_and_derived_total():
    order = PurchaseOrder(id="PO-1001", supplier_id="SUP-001")
    assert order.status == "DRAFT"
    
    order.add_item(sku="SKU-A", quantity=10, unit_price=5.0)
    order.add_item(sku="SKU-B", quantity=2, unit_price=50.0)
    
    assert len(order.items) == 2
    assert order.total_value == 150.0  # (10*5) + (2*50)

def test_purchase_order_enforces_supplier_and_id():
    with pytest.raises(ValueError, match="ID do pedido é obrigatório"):
        PurchaseOrder(id="", supplier_id="SUP-001")
    with pytest.raises(ValueError, match="fornecedor \\(supplier_id\\) é obrigatório"):
        PurchaseOrder(id="PO-1002", supplier_id="")

def test_approval_state_machine_invariants():
    order = PurchaseOrder(id="PO-1003", supplier_id="SUP-001")
    
    # Tentativa de aprovar sem itens
    with pytest.raises(ValueError, match="Não é possível aprovar um pedido sem itens"):
        order.approve()
        
    order.add_item(sku="SKU-C", quantity=100, unit_price=1.5)
    order.approve()
    assert order.status == "APPROVED"
    
    # Tentativa de adicionar itens após aprovação
    with pytest.raises(ValueError, match="Não é possível modificar itens em estado APPROVED"):
        order.add_item(sku="SKU-D", quantity=10, unit_price=2.0)

def test_cancellation_and_reopen_state_machine():
    order = PurchaseOrder(id="PO-1004", supplier_id="SUP-001")
    order.cancel()
    assert order.status == "CANCELLED"
    
    # Tentativa de reabrir um pedido cancelado
    with pytest.raises(ValueError, match="Um pedido CANCELLED está selado e não pode voltar"):
        order.reopen()

def test_cannot_cancel_received_orders():
    order = PurchaseOrder(id="PO-1005", supplier_id="SUP-001", status="PARTIALLY_RECEIVED")
    with pytest.raises(ValueError, match="recebimento físico iniciado não podem ser cancelados"):
        order.cancel()
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Contracts (State Machine Lock)..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado
kippe::checkpoint_create "066" "1.4.0-procurement" "D002" "SUCCESS"

# Sincronização de Governança
kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D002 (PO State Machine)" \
    "D003 — Purchase Order Lines" \
    "2/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Agregado PurchaseOrder e Maquina de Estados (D002) selados contratualmente."
exit 0

