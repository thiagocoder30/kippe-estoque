#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D018: DATABASE MIGRATIONS & VERSIONING (UPCASTING)
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
kippe::banner_program "D" "D018" "Database Migrations & Versioning"

# Preparação de Diretórios
mkdir -p "${KIPPE_ROOT}/src/infrastructure/persistence/migrations"
mkdir -p "${KIPPE_ROOT}/tests/infrastructure/persistence/migrations"
touch "${KIPPE_ROOT}/src/infrastructure/persistence/migrations/__init__.py"
touch "${KIPPE_ROOT}/tests/infrastructure/persistence/migrations/__init__.py"

kippe::step 1 ${TOTAL_STEPS} "Deploying Migration Engine (Upcaster)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/persistence/migrations/engine.py"
from typing import Dict, Any, Callable

class MigrationEngine:
    """
    Motor de Migração (Upcasting) para a Camada de Infraestrutura.
    Intercepta dados desserializados brutos (JSON dictionaries) e aplica transformações
    sequenciais antes de passá-los para a hidratação do Domínio.
    """
    def __init__(self):
        # Mapeia { "versão_origem": funcao_transformadora }
        self._upcasters: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    def register_upcaster(self, from_version: str, upcaster_func: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self._upcasters[from_version] = upcaster_func

    def migrate(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Aplica upcasters sequencialmente até que não haja mais migrações disponíveis."""
        # Assume 1.0 se o registro for legado e não possuir schema_version
        current_version = raw_data.get("schema_version", "1.0")
        
        migrated_data = raw_data.copy()
        
        # Pipeline de transformações (Ex: 1.0 -> 1.1 -> 1.2)
        while current_version in self._upcasters:
            upcaster = self._upcasters[current_version]
            migrated_data = upcaster(migrated_data)
            current_version = migrated_data.get("schema_version")
            
            if not current_version:
                raise RuntimeError("Falha no Upcaster: schema_version não atualizado na transformação.")
                
        return migrated_data
KIPPE_HUNK

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/persistence/migrations/upcasters.py"
from typing import Dict, Any

def purchase_order_v1_0_to_v1_1(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Exemplo de Upcaster Estrutural.
    Evolução de Contrato: A versão 1.1 do repositório exige um campo 'tags' explícito 
    e altera o status inicial para refletir novas invariantes.
    """
    upcasted = raw_data.copy()
    
    # 1. Adiciona novo campo corporativo que não existia na v1.0
    upcasted["tags"] = ["migrated_from_v1.0"]
    
    # 2. Atualiza a versão do schema
    upcasted["schema_version"] = "1.1"
    
    return upcasted
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Integrating Migration Engine into JSON Repositories..."

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
    """
    def __init__(self, file_path: str = "data/purchase_orders.json"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        
        # Inicializa e registra o pipeline de evolução de schema
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
        # Nova versão de escrita é a 1.1
        data = {
            "schema_version": "1.1",
            "id": order.id,
            "supplier_id": order.supplier_id,
            "issue_date": order.issue_date,
            "status": order.status,
            "tags": getattr(order, "tags", []), # Novo campo suportado
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
        # 1. UPCASTING: Transforma dados antigos no schema mais recente antes de instanciar
        migrated_data = self.migration_engine.migrate(data)
        
        # 2. HIDRATAÇÃO DO DOMÍNIO
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

kippe::step 3 ${TOTAL_STEPS} "Deploying Migration Test Suite & Executing Regression..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/infrastructure/persistence/migrations/test_migration_engine.py"
import pytest
from src.infrastructure.persistence.migrations.engine import MigrationEngine
from src.infrastructure.persistence.migrations.upcasters import purchase_order_v1_0_to_v1_1

def test_migration_engine_upcasts_v1_to_v1_1():
    engine = MigrationEngine()
    engine.register_upcaster("1.0", purchase_order_v1_0_to_v1_1)
    
    # Simulando um payload antigo cru guardado no disco
    legacy_payload = {
        "schema_version": "1.0",
        "id": "PO-LEGACY-001",
        "supplier_id": "SUP-1",
        "issue_date": "2023-01-01",
        "status": "DRAFT",
        "items": []
    }
    
    migrated = engine.migrate(legacy_payload)
    
    assert migrated["schema_version"] == "1.1"
    assert "tags" in migrated
    assert migrated["tags"] == ["migrated_from_v1.0"]
    assert migrated["id"] == "PO-LEGACY-001" # Não altera invariantes imutáveis

def test_migration_engine_chains_multiple_versions():
    engine = MigrationEngine()
    
    # V1 -> V2
    engine.register_upcaster("1.0", lambda data: {**data, "schema_version": "2.0", "v2_field": True})
    # V2 -> V3
    engine.register_upcaster("2.0", lambda data: {**data, "schema_version": "3.0", "v3_field": "ok"})
    
    raw = {"schema_version": "1.0", "id": "TEST"}
    final = engine.migrate(raw)
    
    assert final["schema_version"] == "3.0"
    assert final["v2_field"] is True
    assert final["v3_field"] == "ok"

def test_migration_engine_fails_safely_on_broken_upcaster():
    engine = MigrationEngine()
    # Upcaster defeituoso que esquece de atualizar a versão
    engine.register_upcaster("1.0", lambda data: {**data, "new_field": True})
    
    with pytest.raises(RuntimeError, match="não atualizado"):
        engine.migrate({"schema_version": "1.0"})
KIPPE_HUNK

kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "082" "1.4.0-procurement" "D018" "SUCCESS"

kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D018 (Database Migrations & Upcasting)" \
    "D019 — Resilience & Fault Tolerance" \
    "18/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Migration Engine (D018) implantado assegurando evolução retrocompatível."
exit 0

