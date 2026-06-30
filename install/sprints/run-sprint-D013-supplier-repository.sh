#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D013: SUPPLIER REPOSITORY & PERSISTENCE
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
kippe::banner_program "D" "D013" "Supplier Repository & Persistence"

kippe::step 1 ${TOTAL_STEPS} "Deploying Supplier Repository Interface (Domain)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/procurement/supplier_repository.py"
from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.procurement.supplier import Supplier

class SupplierRepository(ABC):
    """
    Interface de Repositório para a Entidade Supplier.
    Mantém o domínio agnóstico em relação ao mecanismo de I/O.
    """
    @abstractmethod
    def save(self, supplier: Supplier) -> None:
        pass

    @abstractmethod
    def get_by_id(self, supplier_id: str) -> Optional[Supplier]:
        pass

    @abstractmethod
    def get_all(self) -> List[Supplier]:
        pass
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Infrastructure Implementations (In-Memory & JSON)..."

# 2.1 In-Memory Implementation
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/persistence/in_memory/supplier_repository.py"
from typing import List, Optional, Dict
from src.domain.procurement.supplier import Supplier
from src.domain.procurement.supplier_repository import SupplierRepository

class InMemorySupplierRepository(SupplierRepository):
    def __init__(self):
        self._storage: Dict[str, Supplier] = {}

    def save(self, supplier: Supplier) -> None:
        self._storage[supplier.id] = supplier

    def get_by_id(self, supplier_id: str) -> Optional[Supplier]:
        return self._storage.get(supplier_id)

    def get_all(self) -> List[Supplier]:
        return list(self._storage.values())
KIPPE_HUNK

# 2.2 JSON Implementation
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/persistence/json/supplier_repository.py"
import os
import json
import tempfile
from typing import List, Optional, Dict, Any
from src.domain.procurement.supplier import Supplier
from src.domain.procurement.supplier_repository import SupplierRepository

class JsonSupplierRepository(SupplierRepository):
    """
    Implementação JSON Atômica com suporte a Schema Versioning.
    """
    def __init__(self, file_path: str = "data/suppliers.json"):
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
        dir_name = os.path.dirname(self.file_path)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix="sup_tmp_", suffix=".json")
        
        with os.fdopen(fd, 'w', encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        os.replace(tmp_path, self.file_path)

    def _serialize(self, supplier: Supplier) -> Dict[str, Any]:
        return {
            "schema_version": "1.0",
            "id": supplier.id,
            "corporate_name": supplier.corporate_name,
            "tax_id": supplier.tax_id,
            "email": supplier.email,
            "status": supplier.status,
            "lead_time_days": supplier.lead_time_days
        }

    def _deserialize(self, data: Dict[str, Any]) -> Supplier:
        # Para entidades planas, o construtor padrão atua como um Factory seguro
        return Supplier(
            id=data["id"],
            corporate_name=data["corporate_name"],
            tax_id=data["tax_id"],
            email=data["email"],
            status=data["status"],
            lead_time_days=data.get("lead_time_days", 0)
        )

    def save(self, supplier: Supplier) -> None:
        data = self._read_all_raw()
        data[supplier.id] = self._serialize(supplier)
        self._atomic_write(data)

    def get_by_id(self, supplier_id: str) -> Optional[Supplier]:
        data = self._read_all_raw()
        if supplier_id not in data:
            return None
        return self._deserialize(data[supplier_id])

    def get_all(self) -> List[Supplier]:
        data = self._read_all_raw()
        return [self._deserialize(obj) for obj in data.values()]
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Deploying Test Suite & Executing Full Regression..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/infrastructure/persistence/json/test_json_supplier_repository.py"
import pytest
import json
from src.domain.procurement.supplier import Supplier
from src.infrastructure.persistence.json.supplier_repository import JsonSupplierRepository
from src.infrastructure.persistence.in_memory.supplier_repository import InMemorySupplierRepository

@pytest.fixture
def temp_json_repo(tmp_path):
    file_path = tmp_path / "test_suppliers.json"
    return JsonSupplierRepository(file_path=str(file_path))

def test_json_supplier_repository_saves_and_retrieves(temp_json_repo):
    sup = Supplier(id="SUP-JSON-01", corporate_name="Tech Corp", tax_id="000", email="x@x.com", lead_time_days=7)
    
    temp_json_repo.save(sup)
    retrieved = temp_json_repo.get_by_id("SUP-JSON-01")
    
    assert retrieved is not None
    assert retrieved.id == "SUP-JSON-01"
    assert retrieved.corporate_name == "Tech Corp"
    assert retrieved.lead_time_days == 7

def test_json_supplier_repository_schema_versioning(temp_json_repo):
    sup = Supplier(id="SUP-JSON-02", corporate_name="Data Inc", tax_id="111", email="y@y.com")
    temp_json_repo.save(sup)
    
    with open(temp_json_repo.file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        
    assert "SUP-JSON-02" in raw_data
    assert raw_data["SUP-JSON-02"]["schema_version"] == "1.0"

def test_in_memory_supplier_repository():
    repo = InMemorySupplierRepository()
    repo.save(Supplier(id="S1", corporate_name="S1", tax_id="1", email="1@1.com"))
    assert repo.get_by_id("S1") is not None
    assert repo.get_by_id("GHOST") is None
    assert len(repo.get_all()) == 1
KIPPE_HUNK

kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "077" "1.4.0-procurement" "D013" "SUCCESS"

kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D013 (Supplier Repository)" \
    "D014 — Application Use Cases (Procurement)" \
    "13/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Interface de Repositório de Supplier e suas implementações atômicas consolidadas (D013)."
exit 0

