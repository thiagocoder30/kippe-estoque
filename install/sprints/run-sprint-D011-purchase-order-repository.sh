#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D011: PURCHASE ORDER REPOSITORY (CLEAN ARCHITECTURE)
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
kippe::banner_program "D" "D011" "Purchase Order Repository (Clean Architecture)"

# Criação da Estrutura de Infraestrutura (Clean Architecture)
mkdir -p "${KIPPE_ROOT}/src/infrastructure/persistence/in_memory"
mkdir -p "${KIPPE_ROOT}/src/infrastructure/persistence/json"
touch "${KIPPE_ROOT}/src/infrastructure/__init__.py"
touch "${KIPPE_ROOT}/src/infrastructure/persistence/__init__.py"
touch "${KIPPE_ROOT}/src/infrastructure/persistence/in_memory/__init__.py"
touch "${KIPPE_ROOT}/src/infrastructure/persistence/json/__init__.py"

kippe::step 1 ${TOTAL_STEPS} "Deploying Repository Interfaces (Domain) and Implementations (Infra)..."

# 1.1 Contrato do Repositório (Domain Layer)
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/procurement/repository.py"
from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.procurement.order import PurchaseOrder

class PurchaseOrderRepository(ABC):
    """
    Interface de Repositório para o Agregado PurchaseOrder.
    Garante que o Domínio dite o contrato sem conhecer a tecnologia de armazenamento.
    """
    @abstractmethod
    def save(self, order: PurchaseOrder) -> None:
        pass

    @abstractmethod
    def get_by_id(self, order_id: str) -> Optional[PurchaseOrder]:
        pass

    @abstractmethod
    def get_all(self) -> List[PurchaseOrder]:
        pass
KIPPE_HUNK

# 1.2 Implementação em Memória (Infrastructure Layer)
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/persistence/in_memory/purchase_order_repository.py"
from typing import List, Optional, Dict
from src.domain.procurement.order import PurchaseOrder
from src.domain.procurement.repository import PurchaseOrderRepository

class InMemoryPurchaseOrderRepository(PurchaseOrderRepository):
    """
    Implementação volátil para testes e isolamento de estado.
    Localizada na camada de Infrastructure, obedecendo ao Dependency Inversion Principle.
    """
    def __init__(self):
        self._storage: Dict[str, PurchaseOrder] = {}

    def save(self, order: PurchaseOrder) -> None:
        self._storage[order.id] = order

    def get_by_id(self, order_id: str) -> Optional[PurchaseOrder]:
        return self._storage.get(order_id)

    def get_all(self) -> List[PurchaseOrder]:
        return list(self._storage.values())
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Test Suite for Persistence Contracts..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/procurement/test_purchase_order_repository.py"
import pytest
from src.domain.procurement.order import PurchaseOrder
from src.infrastructure.persistence.in_memory.purchase_order_repository import InMemoryPurchaseOrderRepository

def test_in_memory_repository_saves_and_retrieves_order():
    repo = InMemoryPurchaseOrderRepository()
    order = PurchaseOrder(id="PO-REPO-001", supplier_id="SUP-CORP")
    
    # Executa Persistência
    repo.save(order)
    
    # Executa Leitura
    retrieved = repo.get_by_id("PO-REPO-001")
    
    assert retrieved is not None
    assert retrieved.id == "PO-REPO-001"
    assert retrieved.supplier_id == "SUP-CORP"
    assert retrieved.status == "DRAFT"

def test_in_memory_repository_returns_none_for_missing_order():
    repo = InMemoryPurchaseOrderRepository()
    assert repo.get_by_id("PO-GHOST-999") is None

def test_in_memory_repository_gets_all_orders():
    repo = InMemoryPurchaseOrderRepository()
    repo.save(PurchaseOrder(id="PO-A", supplier_id="SUP-A"))
    repo.save(PurchaseOrder(id="PO-B", supplier_id="SUP-B"))
    repo.save(PurchaseOrder(id="PO-C", supplier_id="SUP-C"))
    
    all_orders = repo.get_all()
    assert len(all_orders) == 3
    
    # Verifica integridade dos IDs recuperados
    ids = [o.id for o in all_orders]
    assert "PO-A" in ids
    assert "PO-B" in ids
    assert "PO-C" in ids
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Regression Suite..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "075" "1.4.0-procurement" "D011" "SUCCESS"

kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D011 (Purchase Order Repository)" \
    "D012 — JSON Persistence Implementation" \
    "11/20 Sprints" \
    "STABLE"

# Backup de Logs
mkdir -p /sdcard/Download/kippe_logs
cp data/test_*.log /sdcard/Download/kippe_logs/ 2>/dev/null || true

echo -e "\n[STATUS] Estrutura de Infraestrutura e Repository (D011) consolidada com sucesso."
exit 0

