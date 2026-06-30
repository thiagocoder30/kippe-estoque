#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D014: APPLICATION USE CASES (PROCUREMENT)
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
kippe::banner_program "D" "D014" "Application Use Cases (Procurement)"

kippe::step 1 ${TOTAL_STEPS} "Deploying Application Use Cases for Procurement..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/application/procurement/use_cases.py"
from typing import Dict, Any
from src.domain.procurement.order import PurchaseOrder
from src.domain.procurement.repository import PurchaseOrderRepository
from src.domain.procurement.supplier_repository import SupplierRepository

class CreatePurchaseOrderUseCase:
    """Caso de uso para a criação de um novo Pedido de Compra."""
    def __init__(self, po_repo: PurchaseOrderRepository, sup_repo: SupplierRepository):
        self.po_repo = po_repo
        self.sup_repo = sup_repo

    def execute(self, order_id: str, supplier_id: str, items: list[Dict[str, Any]]) -> PurchaseOrder:
        # 1. Validação cruzada com o repositório de fornecedores
        supplier = self.sup_repo.get_by_id(supplier_id)
        if not supplier:
            raise ValueError(f"Fornecedor {supplier_id} não encontrado.")
            
        if supplier.status != "ACTIVE":
            raise ValueError(f"Fornecedor {supplier_id} não está ativo para novas compras.")

        # 2. Criação do Agregado (A regra de negócio habita o Domínio)
        order = PurchaseOrder(id=order_id, supplier_id=supplier_id)
        
        for item in items:
            order.add_item(
                sku=item["sku"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                discount=item.get("discount", 0.0),
                tax=item.get("tax", 0.0)
            )

        # 3. Persistência
        self.po_repo.save(order)
        return order

class ApprovePurchaseOrderUseCase:
    """Caso de uso para aprovação de Pedidos de Compra."""
    def __init__(self, po_repo: PurchaseOrderRepository):
        self.po_repo = po_repo

    def execute(self, order_id: str) -> None:
        order = self.po_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Pedido {order_id} não encontrado.")

        # Delegação do Workflow para o Domínio
        order.approve()
        
        # Persistência do novo estado
        self.po_repo.save(order)
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Test Suite for Application Use Cases..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/application/procurement/test_procurement_use_cases.py"
import pytest
from src.application.procurement.use_cases import CreatePurchaseOrderUseCase, ApprovePurchaseOrderUseCase
from src.infrastructure.persistence.in_memory.purchase_order_repository import InMemoryPurchaseOrderRepository
from src.infrastructure.persistence.in_memory.supplier_repository import InMemorySupplierRepository
from src.domain.procurement.supplier import Supplier
from src.domain.procurement.order import PurchaseOrder

@pytest.fixture
def setup_repos():
    sup_repo = InMemorySupplierRepository()
    po_repo = InMemoryPurchaseOrderRepository()
    
    # Prepara estado inicial
    sup_repo.save(Supplier("SUP-100", "Ativo Corp", "001", "a@a.com", "ACTIVE"))
    sup_repo.save(Supplier("SUP-999", "Blocked Corp", "002", "b@b.com", "BLOCKED"))
    
    # Prepara PO para os testes de aprovação
    po = PurchaseOrder("PO-APP", "SUP-100", status="UNDER_APPROVAL")
    po.add_item("SKU-Z", 10, 5.0)
    # Bypass protection to mock state
    object.__setattr__(po, 'status', 'UNDER_APPROVAL')
    po_repo.save(po)
    
    return sup_repo, po_repo

def test_create_purchase_order_use_case(setup_repos):
    sup_repo, po_repo = setup_repos
    uc = CreatePurchaseOrderUseCase(po_repo, sup_repo)
    
    items = [{"sku": "SKU-A", "quantity": 100, "unit_price": 2.5}]
    order = uc.execute("PO-001", "SUP-100", items)
    
    assert order.id == "PO-001"
    assert order.status == "DRAFT"
    
    # Verifica persistência
    saved = po_repo.get_by_id("PO-001")
    assert saved is not None
    assert len(saved.items) == 1

def test_create_po_fails_if_supplier_not_found(setup_repos):
    sup_repo, po_repo = setup_repos
    uc = CreatePurchaseOrderUseCase(po_repo, sup_repo)
    
    with pytest.raises(ValueError, match="não encontrado"):
        uc.execute("PO-002", "SUP-GHOST", [{"sku": "A", "quantity": 1, "unit_price": 1.0}])

def test_create_po_fails_if_supplier_blocked(setup_repos):
    sup_repo, po_repo = setup_repos
    uc = CreatePurchaseOrderUseCase(po_repo, sup_repo)
    
    with pytest.raises(ValueError, match="não está ativo para novas compras"):
        uc.execute("PO-003", "SUP-999", [{"sku": "B", "quantity": 1, "unit_price": 1.0}])

def test_approve_purchase_order_use_case(setup_repos):
    _, po_repo = setup_repos
    uc = ApprovePurchaseOrderUseCase(po_repo)
    
    uc.execute("PO-APP")
    
    # Verifica que o estado foi alterado e persistido
    saved = po_repo.get_by_id("PO-APP")
    assert saved.status == "APPROVED"

def test_approve_po_fails_if_not_found(setup_repos):
    _, po_repo = setup_repos
    uc = ApprovePurchaseOrderUseCase(po_repo)
    
    with pytest.raises(ValueError, match="não encontrado"):
        uc.execute("PO-GHOST")
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Regression Suite..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "078" "1.4.0-procurement" "D014" "SUCCESS"

kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D014 (Application Use Cases)" \
    "D015 — Procurement CLI / API Gateway" \
    "14/20 Sprints" \
    "STABLE"

# Backup de Logs
mkdir -p /sdcard/Download/kippe_logs
cp data/test_*.log /sdcard/Download/kippe_logs/ 2>/dev/null || true

echo -e "\n[STATUS] Casos de Uso da Camada de Aplicação (D014) implantados com orquestração isolada."
exit 0

