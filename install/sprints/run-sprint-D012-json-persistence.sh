#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D012: JSON PERSISTENCE IMPLEMENTATION
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
kippe::banner_program "D" "D012" "JSON Persistence Implementation"

# Preparação de Estruturas de Teste e Diretórios Locais
mkdir -p "${KIPPE_ROOT}/tests/infrastructure/persistence/json"
touch "${KIPPE_ROOT}/tests/infrastructure/__init__.py"
touch "${KIPPE_ROOT}/tests/infrastructure/persistence/__init__.py"
touch "${KIPPE_ROOT}/tests/infrastructure/persistence/json/__init__.py"

kippe::step 1 ${TOTAL_STEPS} "Deploying Atomic JSON Repository (Infrastructure Layer)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/persistence/json/purchase_order_repository.py"
import os
import json
import tempfile
from typing import List, Optional, Dict, Any
from src.domain.procurement.order import PurchaseOrder, PurchaseOrderLine, MonetaryValue
from src.domain.procurement.repository import PurchaseOrderRepository

class JsonPurchaseOrderRepository(PurchaseOrderRepository):
    """
    Implementação concreta de persistência em ficheiro JSON.
    Assegura escritas atómicas e implementa versionamento de schema (schema_version).
    Totalmente invisível para o Domínio.
    """
    def __init__(self, file_path: str = "data/purchase_orders.json"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def _read_all_raw(self) -> Dict[str, Any]:
        if not os.path.exists(self.file_path):
            return {}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def _atomic_write(self, data: Dict[str, Any]) -> None:
        """Executa gravação temporária seguida de atomic rename para evitar corrupção de ficheiro."""
        dir_name = os.path.dirname(self.file_path)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix="po_tmp_", suffix=".json")
        
        with os.fdopen(fd, 'w', encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        os.replace(tmp_path, self.file_path)

    def _serialize(self, order: PurchaseOrder) -> Dict[str, Any]:
        return {
            "schema_version": "1.0",
            "id": order.id,
            "supplier_id": order.supplier_id,
            "issue_date": order.issue_date,
            "status": order.status,
            "items": [
                {
                    "sku": item.sku,
                    "quantity": item.quantity,
                    "unit_price": {"amount": item.unit_price.amount, "currency": item.unit_price.currency},
                    "discount": {"amount": item.discount.amount, "currency": item.discount.currency},
                    "tax": {"amount": item.tax.amount, "currency": item.tax.currency},
                    "received_quantity": item.received_quantity
                } for item in order.items
            ]
        }

    def _deserialize(self, data: Dict[str, Any]) -> PurchaseOrder:
        order = PurchaseOrder(
            id=data["id"],
            supplier_id=data["supplier_id"],
            issue_date=data["issue_date"],
            status=data["status"]
        )
        items = []
        for i_data in data.get("items", []):
            line = PurchaseOrderLine(
                sku=i_data["sku"],
                quantity=i_data["quantity"],
                unit_price=MonetaryValue(**i_data["unit_price"]),
                discount=MonetaryValue(**i_data["discount"]),
                tax=MonetaryValue(**i_data["tax"])
            )
            object.__setattr__(line, 'received_quantity', i_data.get("received_quantity", 0))
            items.append(line)
        
        # Bypass nas regras de modificação tardia (__post_init__ e add_item) via reflexão de atributos
        # Fundamental para restaurar o objeto de forma fidedigna a partir do banco de dados
        object.__setattr__(order, 'items', items)
        return order

    def save(self, order: PurchaseOrder) -> None:
        data = self._read_all_raw()
        data[order.id] = self._serialize(order)
        self._atomic_write(data)

    def get_by_id(self, order_id: str) -> Optional[PurchaseOrder]:
        data = self._read_all_raw()
        if order_id not in data:
            return None
        return self._deserialize(data[order_id])

    def get_all(self) -> List[PurchaseOrder]:
        data = self._read_all_raw()
        return [self._deserialize(obj) for obj in data.values()]
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Test Suite for JSON Infrastructure..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/infrastructure/persistence/json/test_json_purchase_order_repository.py"
import os
import json
import pytest
from src.domain.procurement.order import PurchaseOrder
from src.infrastructure.persistence.json.purchase_order_repository import JsonPurchaseOrderRepository

@pytest.fixture
def temp_json_repo(tmp_path):
    """Fornece um repositório isolado usando o diretório temporário do pytest"""
    file_path = tmp_path / "test_purchase_orders.json"
    return JsonPurchaseOrderRepository(file_path=str(file_path))

def test_json_repository_saves_and_retrieves_order(temp_json_repo):
    order = PurchaseOrder(id="PO-JSON-1", supplier_id="SUP-JSON")
    order.add_item("SKU-1", 10, 50.0)
    
    # Grava e lê do disco
    temp_json_repo.save(order)
    retrieved = temp_json_repo.get_by_id("PO-JSON-1")
    
    assert retrieved is not None
    assert retrieved.id == "PO-JSON-1"
    assert retrieved.supplier_id == "SUP-JSON"
    assert len(retrieved.items) == 1
    assert retrieved.items[0].sku == "SKU-1"
    assert retrieved.items[0].unit_price.amount == 50.0

def test_json_repository_atomic_write_creates_schema_version(temp_json_repo):
    order = PurchaseOrder(id="PO-JSON-2", supplier_id="SUP-JSON")
    temp_json_repo.save(order)
    
    # Validação estrutural do JSON gerado
    with open(temp_json_repo.file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        
    assert "PO-JSON-2" in raw_data
    assert raw_data["PO-JSON-2"]["schema_version"] == "1.0"

def test_json_repository_get_all(temp_json_repo):
    temp_json_repo.save(PurchaseOrder(id="PO-A", supplier_id="S-A"))
    temp_json_repo.save(PurchaseOrder(id="PO-B", supplier_id="S-B"))
    
    orders = temp_json_repo.get_all()
    assert len(orders) == 2
    
    ids = [o.id for o in orders]
    assert "PO-A" in ids
    assert "PO-B" in ids

def test_json_repository_returns_none_for_missing(temp_json_repo):
    assert temp_json_repo.get_by_id("PO-GHOST") is None
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Regression Suite..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "076" "1.4.0-procurement" "D012" "SUCCESS"

kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D012 (JSON Persistence Implementation)" \
    "D013 — Supplier Repository & Persistence" \
    "12/20 Sprints" \
    "STABLE"

# Backup de Logs
mkdir -p /sdcard/Download/kippe_logs
cp data/test_*.log /sdcard/Download/kippe_logs/ 2>/dev/null || true

echo -e "\n[STATUS] Infraestrutura JSON com Escrita Atómica e Versionamento (D012) consolidada com sucesso."
exit 0

