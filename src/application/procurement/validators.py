from typing import Dict, Any, List
from src.security.exceptions import ValidationException

class CreatePurchaseOrderValidator:
    """Validador de Entrada (Request Validator) isolado."""
    @staticmethod
    def validate(order_id: str, supplier_id: str, items: List[Dict[str, Any]]) -> None:
        if not order_id or not isinstance(order_id, str):
            raise ValidationException("order_id inválido ou ausente na requisição.")
        if not supplier_id or not isinstance(supplier_id, str):
            raise ValidationException("supplier_id inválido ou ausente na requisição.")
        if not items or not isinstance(items, list):
            raise ValidationException("A lista de itens não pode estar vazia.")
            
        for item in items:
            if "sku" not in item or "quantity" not in item or "unit_price" not in item:
                raise ValidationException("Item malformado. Exigido: sku, quantity, unit_price.")
            if not isinstance(item["quantity"], int) or item["quantity"] <= 0:
                raise ValidationException(f"Quantidade inválida para o SKU {item.get('sku')}.")
            if not isinstance(item["unit_price"], (int, float)) or item["unit_price"] < 0:
                raise ValidationException(f"Preço inválido para o SKU {item.get('sku')}.")
