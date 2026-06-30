from typing import Dict, Any
from src.domain.procurement.order import PurchaseOrder
from src.domain.procurement.repository import PurchaseOrderRepository
from src.domain.procurement.supplier_repository import SupplierRepository
from src.security.correlation import ExecutionContext
from src.security.exceptions import NotFoundException, BusinessRuleViolation
from src.application.procurement.validators import CreatePurchaseOrderValidator

class CreatePurchaseOrderUseCase:
    """Use Case Purificado. Sem referências a infraestrutura transversal."""
    def __init__(self, po_repo: PurchaseOrderRepository, sup_repo: SupplierRepository):
        self.po_repo = po_repo
        self.sup_repo = sup_repo

    def execute(self, context: ExecutionContext, order_id: str, supplier_id: str, items: list[Dict[str, Any]]) -> PurchaseOrder:
        CreatePurchaseOrderValidator.validate(order_id, supplier_id, items)

        supplier = self.sup_repo.get_by_id(supplier_id)
        if not supplier:
            raise NotFoundException(f"Fornecedor {supplier_id} não encontrado.")
        if supplier.status != "ACTIVE":
            raise BusinessRuleViolation(f"Fornecedor {supplier_id} não está ativo para novas compras.")

        order = PurchaseOrder(id=order_id, supplier_id=supplier_id)
        for item in items:
            order.add_item(
                sku=item["sku"], quantity=item["quantity"],
                unit_price=item["unit_price"], discount=item.get("discount", 0.0), tax=item.get("tax", 0.0)
            )

        self.po_repo.save(order)
        return order

class ApprovePurchaseOrderUseCase:
    def __init__(self, po_repo: PurchaseOrderRepository):
        self.po_repo = po_repo

    def execute(self, context: ExecutionContext, order_id: str) -> None:
        order = self.po_repo.get_by_id(order_id)
        if not order:
            raise NotFoundException(f"Pedido {order_id} não encontrado.")

        try:
            order.approve()
            self.po_repo.save(order)
        except ValueError as e:
            raise BusinessRuleViolation(str(e))
