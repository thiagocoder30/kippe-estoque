import json
from typing import List, Dict, Any
from src.domain.product import Product
from src.domain.batch import Batch
from src.domain.snapshot import InventorySnapshot
class SnapshotEngine:
    """
    Domain Service: Snapshot Engine
    Gerador e restaurador de estados para auditoria e performance.
    """
    @staticmethod
    def capture(snapshot_id: str, products: List[Product], operator_id: str = "SYSTEM") -> InventorySnapshot:
        data = []
        for p in products:
            batches_data = {k: v.__dict__ for k, v in p.batches.items()}
            p_data = {
                "id": p.id,
                "name": p.name,
                "quantity": p.quantity,
                "reserved_quantity": p.reserved_quantity,
                "unit_of_measure": p.unit_of_measure,
                "status": p.status,
                "category_id": p.category_id,
                "batches": batches_data
            }
            data.append(p_data)
        
        return InventorySnapshot(
            id=snapshot_id,
            payload=json.dumps(data),
            created_by=operator_id
        )
    @staticmethod
    def restore(snapshot: InventorySnapshot) -> List[Product]:
        try:
            data = json.loads(snapshot.payload)
        except json.JSONDecodeError:
            raise ValueError("Payload de Snapshot corrompido ou inválido.")
        restored_products = []
        for p_data in data:
            batches = {}
            for b_code, b_info in p_data.get("batches", {}).items():
                batches[b_code] = Batch(**b_info)
            
            prod = Product(
                id=p_data["id"],
                name=p_data["name"],
                quantity=p_data["quantity"],
                reserved_quantity=p_data.get("reserved_quantity", 0),
                unit_of_measure=p_data.get("unit_of_measure", "un"),
                status=p_data.get("status", "ATIVO"),
                category_id=p_data.get("category_id")
            )
            prod.batches = batches
            restored_products.append(prod)
            
        return restored_products
