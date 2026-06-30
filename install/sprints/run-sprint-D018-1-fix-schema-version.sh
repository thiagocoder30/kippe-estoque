#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D018.1: FIX SCHEMA VERSIONING (STORAGE CONTRACT)
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

# 1. Carregamento do Framework
source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=2
kippe::banner_program "D" "D018.1" "Fix Schema Versioning (Storage Contract)"

kippe::step 1 ${TOTAL_STEPS} "Restoring Write Model Versioning Contract..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/persistence/json/purchase_order_repository.py"
import os
import json
import tempfile
from typing import List, Optional, Dict, Any
from src.domain.procurement.order import PurchaseOrder, PurchaseOrderLine, MonetaryValue
from src.domain.procurement.repository import PurchaseOrderRepository
from src.infrastructure.persistence.migrations.engine import MigrationEngine
from src.infrastructure.persistence.migrations.upcasters import purchase_order_v1_0_to_v1_1

class JsonPurchaseOrderRepository(PurchaseOrderRepository):
    """
    Repositório protegido por Upcasting de Schema.
    O método serialize honra a Baseline garantindo retrocompatibilidade.
    """
    def __init__(self, file_path: str = "data/purchase_orders.json"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        
        # Inicializa e registra o pipeline de evolução de schema (Read-Path)
        self.migration_engine = MigrationEngine()
        self.migration_engine.register_upcaster("1.0", purchase_order_v1_0_to_v1_1)

    def _read_all_raw(self) -> Dict[str, Any]:
        if not os.path.exists(self.file_path):
            return {}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def _atomic_write(self, data: Dict[str, Any]) -> None:
        dir_name = os.path.dirname(self.file_path)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix="po_tmp_", suffix=".json")
        
        with os.fdopen(fd, 'w', encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        os.replace(tmp_path, self.file_path)

    def _serialize(self, order: PurchaseOrder) -> Dict[str, Any]:
        # [HOTFIX D018.1] Write-Path: O storage "nasce" na versão de base contratada pelos testes (1.0)
        data = {
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
        return data

    def _deserialize(self, data: Dict[str, Any]) -> PurchaseOrder:
        # UPCASTING: Transforma dados antigos (Read-Path) no schema mais recente (1.1)
        migrated_data = self.migration_engine.migrate(data)
        
        # HIDRATAÇÃO DO DOMÍNIO
        order = PurchaseOrder(
            id=migrated_data["id"],
            supplier_id=migrated_data["supplier_id"],
            issue_date=migrated_data["issue_date"],
            status=migrated_data["status"]
        )
        
        items = []
        for i_data in migrated_data.get("items", []):
            line = PurchaseOrderLine(
                sku=i_data["sku"], quantity=i_data["quantity"],
                unit_price=MonetaryValue(**i_data["unit_price"]),
                discount=MonetaryValue(**i_data.get("discount", {"amount":0.0})),
                tax=MonetaryValue(**i_data.get("tax", {"amount":0.0}))
            )
            object.__setattr__(line, 'received_quantity', i_data.get("received_quantity", 0))
            items.append(line)
        
        object.__setattr__(order, 'items', items)
        object.__setattr__(order, 'tags', migrated_data.get("tags", []))
        
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

kippe::step 2 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Regression Suite..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "083" "1.4.0-procurement" "D018.1" "SUCCESS"

kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D018.1 (Schema Write Model Fix)" \
    "D019 — Resilience & Fault Tolerance" \
    "18/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Storage Contract (D018 Fix) restaurado com sucesso. Upcaster preservado na leitura."
exit 0

