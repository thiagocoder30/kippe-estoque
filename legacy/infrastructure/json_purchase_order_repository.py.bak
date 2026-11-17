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
