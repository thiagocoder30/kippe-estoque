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
