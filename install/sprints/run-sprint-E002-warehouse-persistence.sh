#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E002: WAREHOUSE PERSISTENCE & LEAN MODEL
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=3
kippe::banner_program "E" "E002" "Warehouse Persistence"

kippe::step 1 ${TOTAL_STEPS} "Deploying JSON Warehouse Repository..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/persistence/json/warehouse_repository.py"
import os
import json
import tempfile
from typing import List, Optional, Dict, Any
from src.domain.warehouse.topology import Warehouse, StorageLocation
from src.domain.warehouse.repository import WarehouseRepository

class JsonWarehouseRepository(WarehouseRepository):
    def __init__(self, file_path: str = "data/warehouses.json"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def save(self, warehouse: Warehouse) -> None:
        data = self._read_all()
        data[warehouse.id] = {
            "id": warehouse.id,
            "name": warehouse.name,
            "locations": [{"id": l.id, "name": l.name, "is_active": l.is_active} for l in warehouse.locations]
        }
        self._atomic_write(data)

    def get_by_id(self, warehouse_id: str) -> Optional[Warehouse]:
        data = self._read_all()
        if warehouse_id not in data:
            return None
        
        raw = data[warehouse_id]
        wh = Warehouse(id=raw["id"], name=raw["name"])
        for loc in raw["locations"]:
            l = wh.add_location(loc["id"], loc["name"])
            if not loc["is_active"]: l.disable()
        return wh

    def get_all(self) -> List[Warehouse]:
        data = self._read_all()
        return [self.get_by_id(wid) for wid in data.keys()]

    def _read_all(self) -> Dict[str, Any]:
        if not os.path.exists(self.file_path): return {}
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _atomic_write(self, data: Dict[str, Any]) -> None:
        dir_name = os.path.dirname(self.file_path)
        fd, tmp = tempfile.mkstemp(dir=dir_name, suffix=".json")
        with os.fdopen(fd, 'w', encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.file_path)
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Persistence Tests..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/infrastructure/persistence/test_warehouse_repo.py"
import pytest
from src.domain.warehouse.topology import Warehouse
from src.infrastructure.persistence.json.warehouse_repository import JsonWarehouseRepository

def test_warehouse_repo_persistence(tmp_path):
    file_path = tmp_path / "warehouses.json"
    repo = JsonWarehouseRepository(file_path=str(file_path))
    
    wh = Warehouse(id="WH-001", name="Armazém A")
    wh.add_location("LOC-1", "Zona Direita")
    
    repo.save(wh)
    loaded = repo.get_by_id("WH-001")
    
    assert loaded is not None
    assert loaded.name == "Armazém A"
    assert len(loaded.locations) == 1
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Regression and Governance Update..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

kippe::checkpoint_create "092" "1.5.0-platform" "E002" "SUCCESS"

kippe::governance_sync "E" "Warehouse" "4" "Foundation" "E.1" "Persistence" "E002 (Persistence)" "E003 (Ledger)" "2/20" "STABLE"

echo -e "\n[STATUS] Persistência do Armazém Lean (E002) consolidada."
exit 0

