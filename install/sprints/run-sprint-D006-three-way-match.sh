#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D006: THREE-WAY MATCH (DOMAIN SERVICE)
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
kippe::banner_program "D" "D006" "Three-Way Match Engine"

kippe::step 1 ${TOTAL_STEPS} "Deploying Supplier Invoice Entity and MatchResult Value Object..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/procurement/invoice.py"
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
KIPPE_HUNK

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/procurement/three_way_match.py"
from dataclasses import dataclass, field
from typing import List, Dict
from src.domain.procurement.order import PurchaseOrder
from src.domain.procurement.invoice import SupplierInvoice

@dataclass(frozen=True)
class MatchResult:
    """
    Value Object: Resultado imutável da conciliação.
    Não altera o estado do pedido, apenas expõe a auditoria matemática.
    """
    is_matched: bool
    divergences: List[str] = field(default_factory=list)
    quantity_delta: Dict[str, int] = field(default_factory=dict)
    price_delta: Dict[str, float] = field(default_factory=dict)

class ThreeWayMatchEngine:
    """
    Domain Service: Avalia a tríade (1. Pedido Aprovado vs 2. Recebimento Físico vs 3. Fatura)
    """
    @staticmethod
    def evaluate(order: PurchaseOrder, invoice: SupplierInvoice) -> MatchResult:
        divergences = []
        q_delta = {}
        p_delta = {}

        # 1. Validação de Vínculo de Fornecedor
        if order.supplier_id != invoice.supplier_id:
            divergences.append("Fornecedor da nota fiscal difere do fornecedor do pedido de compra.")

        order_lines = {item.sku: item for item in order.items}
        
        for inv_line in invoice.lines:
            po_line = order_lines.get(inv_line.sku)
            
            # 2. Validação de Escopo (Item não solicitado)
            if not po_line:
                divergences.append(f"SKU {inv_line.sku} faturado, mas não consta no pedido de compra.")
                continue
            
            # 3. Validação de Três Pontas: Quantidade (Faturado vs Fisicamente Recebido)
            if inv_line.quantity != po_line.received_quantity:
                delta = inv_line.quantity - po_line.received_quantity
                q_delta[inv_line.sku] = delta
                divergences.append(
                    f"Divergência de quantidade no SKU {inv_line.sku}: Faturado={inv_line.quantity}, "
                    f"Fisicamente Recebido={po_line.received_quantity}."
                )

            # 4. Validação de Preço (Faturado vs Pedido Aprovado)
            if inv_line.unit_price.amount != po_line.unit_price.amount:
                delta_price = inv_line.unit_price.amount - po_line.unit_price.amount
                p_delta[inv_line.sku] = delta_price
                divergences.append(
                    f"Divergência de preço no SKU {inv_line.sku}: Faturado={inv_line.unit_price.amount}, "
                    f"Aprovado no Pedido={po_line.unit_price.amount}."
                )

        is_matched = len(divergences) == 0
        return MatchResult(
            is_matched=is_matched,
            divergences=divergences,
            quantity_delta=q_delta,
            price_delta=p_delta
        )
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Strict Contract Test Suite for Three-Way Match Engine..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/procurement/test_three_way_match.py"
import pytest
from src.domain.procurement.order import PurchaseOrder, MonetaryValue
from src.domain.procurement.invoice import SupplierInvoice, SupplierInvoiceLine
from src.domain.procurement.three_way_match import ThreeWayMatchEngine

def setup_base_order_and_receipt():
    order = PurchaseOrder(id="PO-3W-001", supplier_id="SUP-CORP")
    order.add_item(sku="SKU-A", quantity=100, unit_price=10.0)
    order.add_item(sku="SKU-B", quantity=50, unit_price=20.0)
    order.submit()
    order.start_approval()
    order.approve()
    order.place_order()
    
    # Simulação de Recebimento Físico Perfeito
    order.receive_item("SKU-A", 100)
    order.receive_item("SKU-B", 50)
    return order

def test_three_way_match_perfect_scenario():
    order = setup_base_order_and_receipt()
    
    invoice = SupplierInvoice(invoice_number="NFE-001", supplier_id="SUP-CORP")
    invoice.lines.append(SupplierInvoiceLine(sku="SKU-A", quantity=100, unit_price=MonetaryValue(10.0)))
    invoice.lines.append(SupplierInvoiceLine(sku="SKU-B", quantity=50, unit_price=MonetaryValue(20.0)))
    
    result = ThreeWayMatchEngine.evaluate(order, invoice)
    
    assert result.is_matched is True
    assert len(result.divergences) == 0
    assert not result.quantity_delta
    assert not result.price_delta

def test_three_way_match_fails_on_quantity_divergence():
    order = setup_base_order_and_receipt()
    
    invoice = SupplierInvoice(invoice_number="NFE-002", supplier_id="SUP-CORP")
    # Fornecedor cobrando 110 itens, mas recebemos fisicamente 100
    invoice.lines.append(SupplierInvoiceLine(sku="SKU-A", quantity=110, unit_price=MonetaryValue(10.0)))
    
    result = ThreeWayMatchEngine.evaluate(order, invoice)
    
    assert result.is_matched is False
    assert "Divergência de quantidade no SKU SKU-A" in result.divergences[0]
    assert result.quantity_delta["SKU-A"] == 10  # Delta positivo de 10 na fatura

def test_three_way_match_fails_on_price_divergence():
    order = setup_base_order_and_receipt()
    
    invoice = SupplierInvoice(invoice_number="NFE-003", supplier_id="SUP-CORP")
    # Fornecedor cobrando preço maior que o aprovado no pedido
    invoice.lines.append(SupplierInvoiceLine(sku="SKU-A", quantity=100, unit_price=MonetaryValue(12.5)))
    
    result = ThreeWayMatchEngine.evaluate(order, invoice)
    
    assert result.is_matched is False
    assert "Divergência de preço no SKU SKU-A" in result.divergences[0]
    assert result.price_delta["SKU-A"] == 2.5  # Delta financeiro positivo

def test_three_way_match_fails_on_unauthorized_sku():
    order = setup_base_order_and_receipt()
    
    invoice = SupplierInvoice(invoice_number="NFE-004", supplier_id="SUP-CORP")
    invoice.lines.append(SupplierInvoiceLine(sku="SKU-FANTASMA", quantity=10, unit_price=MonetaryValue(5.0)))
    
    result = ThreeWayMatchEngine.evaluate(order, invoice)
    
    assert result.is_matched is False
    assert "não consta no pedido de compra" in result.divergences[0]

def test_three_way_match_fails_on_supplier_mismatch():
    order = setup_base_order_and_receipt()
    
    # Fatura emitida por fornecedor diferente do PO aprovado
    invoice = SupplierInvoice(invoice_number="NFE-005", supplier_id="SUP-FRAUDE")
    result = ThreeWayMatchEngine.evaluate(order, invoice)
    
    assert result.is_matched is False
    assert "difere do fornecedor do pedido" in result.divergences[0]
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Base Contracts (Domain Lock)..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado Inaugural do Programa D
kippe::checkpoint_create "070" "1.4.0-procurement" "D006" "SUCCESS"

# Atualização da Governança para o Novo Programa
kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D006 (Three-Way Match)" \
    "D007 — Supplier Ledger / Performance" \
    "6/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Domain Service de Three-Way Match (D006) estabelecido."
exit 0

