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
