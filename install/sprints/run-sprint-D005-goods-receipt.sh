#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D005: GOODS RECEIPT (APPLICATION SERVICE)
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

TOTAL_STEPS=4
kippe::banner_program "D" "D005" "Goods Receipt Application Service"

# Criação da Camada de Aplicação
mkdir -p "${KIPPE_ROOT}/src/application/procurement"
mkdir -p "${KIPPE_ROOT}/tests/application/procurement"
touch "${KIPPE_ROOT}/src/application/__init__.py"
touch "${KIPPE_ROOT}/src/application/procurement/__init__.py"
touch "${KIPPE_ROOT}/tests/application/__init__.py"
touch "${KIPPE_ROOT}/tests/application/procurement/__init__.py"

kippe::step 1 ${TOTAL_STEPS} "Upgrading PurchaseOrder Aggregate (Data-Driven Transitions)..."

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
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Application Service (Goods Receipt)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/application/procurement/receive_goods_service.py"
from dataclasses import dataclass
from typing import Dict
from datetime import datetime
from src.domain.procurement.order import PurchaseOrder
from src.domain.product import Product
from src.domain.batch import Batch

@dataclass
class ReceiveGoodsCommand:
    order_id: str
    items_received: Dict[str, int]
    warehouse_id: str
    operator_id: str
    # Utilizado para simplificar o preenchimento da data de expiração no mock E2E
    expiration_date: str = "2099-12-31" 

class ReceiveGoodsService:
    """
    Application Service: Orquestra a transição de estado no Domínio de Compras
    e interage com o Contrato Público do Domínio de Inventário (Baseline 1.3.0 Frozen).
    """
    @staticmethod
    def execute(command: ReceiveGoodsCommand, order: PurchaseOrder, inventory_catalog: Dict[str, Product]) -> None:
        if order.id != command.order_id:
            raise ValueError("Inconsistência: O comando não corresponde ao pedido fornecido.")
            
        for sku, qty in command.items_received.items():
            if qty <= 0:
                raise ValueError(f"Quantidade de recebimento inválida para o SKU {sku}.")

            # 1. Atualiza Domínio de Procurement (Máquina de Estados)
            order.receive_item(sku, qty)
            
            # Recupera a linha para extrair o custo financeiro unitário negociado
            line = next(item for item in order.items if item.sku == sku)
            
            # 2. Interage com Domínio de Inventário (Criando o Lote)
            product = inventory_catalog.get(sku)
            if not product:
                raise ValueError(f"Falha de Integração: SKU {sku} não encontrado no catálogo de inventário.")
                
            batch_code = f"GR-{order.id}-{sku}-{datetime.now().strftime('%H%M%S')}"
            
            # Utiliza o contrato estrito consolidado na Sprint INF008
            new_batch = Batch(
                code=batch_code,
                product_id=sku,
                quantity=qty,
                expiration_date=command.expiration_date,
                cost_per_unit=line.unit_price.amount,
                warehouse_id=command.warehouse_id,
                supplier=order.supplier_id
            )
            
            product.batches[batch_code] = new_batch
            product.quantity += qty
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Aligning D004 Tests and Deploying D005 Application Tests..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/procurement/test_purchase_order_aggregate.py"
import pytest
from src.domain.procurement.order import PurchaseOrder, PurchaseOrderLine, MonetaryValue

def test_monetary_value_object():
    v1 = MonetaryValue(10.50)
    v2 = MonetaryValue(5.25)
    assert (v1 + v2).amount == 15.75
    assert (v1 - v2).amount == 5.25

def test_purchase_order_line_subtotal():
    line = PurchaseOrderLine(sku="SKU-A", quantity=10, unit_price=MonetaryValue(100.0), discount=MonetaryValue(100.0), tax=MonetaryValue(50.0))
    assert line.subtotal.amount == 950.0

def test_purchase_order_creation_and_derived_total():
    order = PurchaseOrder(id="PO-1001", supplier_id="SUP-001")
    order.add_item(sku="SKU-A", quantity=10, unit_price=5.0)
    order.add_item(sku="SKU-B", quantity=2, unit_price=50.0, discount=10.0, tax=5.0)
    assert order.total_value.amount == 145.0

def test_approval_workflow_invariants():
    order = PurchaseOrder(id="PO-WF-003", supplier_id="SUP-99")
    with pytest.raises(ValueError, match="Não é possível submeter um pedido sem itens"):
        order.submit()
    order.add_item("SKU-K", 1, 100.0)
    with pytest.raises(ValueError, match="O pedido precisa estar APPROVED"):
        order.place_order()
    with pytest.raises(ValueError, match="Impedir recebimento antes de ORDERED"):
        order.receive_item("SKU-K", 1)

def test_data_driven_receiving_workflow():
    order = PurchaseOrder(id="PO-WF-005", supplier_id="SUP-99")
    order.add_item("SKU-X", 10, 10.0)
    order.add_item("SKU-Y", 5, 20.0)
    
    order.submit()
    order.start_approval()
    order.approve()
    order.place_order()
    assert order.status == "ORDERED"
    
    # Recebimento Parcial
    order.receive_item("SKU-X", 5)
    assert order.status == "PARTIALLY_RECEIVED"
    
    # Recebimento Complementar
    order.receive_item("SKU-X", 5)
    order.receive_item("SKU-Y", 5)
    assert order.status == "RECEIVED"
    
    # Fechamento
    order.close()
    assert order.status == "CLOSED"
    
    # Excedente físico
    with pytest.raises(ValueError, match="Impedir recebimento antes de ORDERED ou após finalizado"):
        order.receive_item("SKU-X", 1)
KIPPE_HUNK

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/application/procurement/test_receive_goods_service.py"
import pytest
from src.domain.procurement.order import PurchaseOrder
from src.domain.product import Product
from src.application.procurement.receive_goods_service import ReceiveGoodsCommand, ReceiveGoodsService

def test_application_service_orchestrates_procurement_and_inventory():
    # 1. Configuração do Mock de Inventário (Core Frozen)
    p1 = Product(id="SKU-GR-1", name="Placa de Video", quantity=0)
    catalog = {"SKU-GR-1": p1}
    
    # 2. Configuração do Pedido de Compras
    order = PurchaseOrder(id="PO-2001", supplier_id="SUP-MASTER")
    order.add_item(sku="SKU-GR-1", quantity=50, unit_price=2500.0)
    order.submit()
    order.start_approval()
    order.approve()
    order.place_order()
    
    # 3. Comando de Aplicação
    cmd = ReceiveGoodsCommand(
        order_id="PO-2001",
        items_received={"SKU-GR-1": 50},
        warehouse_id="CD-SUL",
        operator_id="OP-RECEBIMENTO"
    )
    
    # 4. Execução do Serviço
    ReceiveGoodsService.execute(command=cmd, order=order, inventory_catalog=catalog)
    
    # 5. Asserções (Contratos Respeitados em ambos os Bounded Contexts)
    assert order.status == "RECEIVED"
    assert p1.quantity == 50
    
    # Verifica se o lote foi fisicamente criado no Inventário com os atributos da Compra
    batches = list(p1.batches.values())
    assert len(batches) == 1
    batch = batches[0]
    
    assert batch.product_id == "SKU-GR-1"
    assert batch.quantity == 50
    assert batch.cost_per_unit == 2500.0
    assert batch.supplier == "SUP-MASTER"
    assert batch.code.startswith("GR-PO-2001-SKU-GR-1-")
KIPPE_HUNK

kippe::step 4 ${TOTAL_STEPS} "Verifying Syntax and Executing Contracts (Cross-Domain Lock)..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "069" "1.4.0-procurement" "D005" "SUCCESS"

kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D005 (Goods Receipt Application Service)" \
    "D006 — Three Way Match" \
    "5/20 Sprints" \
    "STABLE"

# Backup dos logs de teste para diretório externo seguro
mkdir -p /sdcard/Download/kippe_logs
cp data/test_*.log /sdcard/Download/kippe_logs/ 2>/dev/null || true

echo -e "\n[STATUS] Integração entre Procurement e Inventory (D005) orquestrada com sucesso via Application Service."
exit 0

