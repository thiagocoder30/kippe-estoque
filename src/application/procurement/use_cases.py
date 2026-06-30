from typing import Dict, Any
from src.domain.procurement.order import PurchaseOrder
from src.domain.procurement.repository import PurchaseOrderRepository
from src.domain.procurement.supplier_repository import SupplierRepository
from src.security.correlation import ExecutionContext
from src.security.audit import AuditLogger
from src.security.exceptions import NotFoundException, BusinessRuleViolation
from src.application.procurement.validators import CreatePurchaseOrderValidator

class CreatePurchaseOrderUseCase:
    def __init__(self, po_repo: PurchaseOrderRepository, sup_repo: SupplierRepository, audit_logger: AuditLogger = None):
        self.po_repo = po_repo
        self.sup_repo = sup_repo
        self.audit = audit_logger or AuditLogger()

    def execute(self, context: ExecutionContext, order_id: str, supplier_id: str, items: list[Dict[str, Any]]) -> PurchaseOrder:
        # 1. Validação de Entrada
        CreatePurchaseOrderValidator.validate(order_id, supplier_id, items)

        # 2. Resolução de Entidades (Lança exceções corporativas em vez de ValueError genérico)
        supplier = self.sup_repo.get_by_id(supplier_id)
        if not supplier:
            self.audit.log_operation(context, "CREATE_PO", order_id, "FAILED", {"reason": "Supplier Not Found"})
            raise NotFoundException(f"Fornecedor {supplier_id} não encontrado.")
            
        if supplier.status != "ACTIVE":
            self.audit.log_operation(context, "CREATE_PO", order_id, "FAILED", {"reason": "Supplier Blocked"})
            raise BusinessRuleViolation(f"Fornecedor {supplier_id} não está ativo para novas compras.")

        # 3. Execução de Domínio
        order = PurchaseOrder(id=order_id, supplier_id=supplier_id)
        for item in items:
            order.add_item(
                sku=item["sku"], quantity=item["quantity"],
                unit_price=item["unit_price"], discount=item.get("discount", 0.0), tax=item.get("tax", 0.0)
            )

        # 4. Persistência e Auditoria Transversal
        self.po_repo.save(order)
        self.audit.log_operation(context, "CREATE_PO", order.id, "SUCCESS")
        return order

class ApprovePurchaseOrderUseCase:
    def __init__(self, po_repo: PurchaseOrderRepository, audit_logger: AuditLogger = None):
        self.po_repo = po_repo
        self.audit = audit_logger or AuditLogger()

    def execute(self, context: ExecutionContext, order_id: str) -> None:
        order = self.po_repo.get_by_id(order_id)
        if not order:
            self.audit.log_operation(context, "APPROVE_PO", order_id, "FAILED", {"reason": "PO Not Found"})
            raise NotFoundException(f"Pedido {order_id} não encontrado.")

        try:
            order.approve()
            self.po_repo.save(order)
            self.audit.log_operation(context, "APPROVE_PO", order.id, "SUCCESS")
        except ValueError as e:
            self.audit.log_operation(context, "APPROVE_PO", order.id, "FAILED", {"reason": str(e)})
            raise BusinessRuleViolation(str(e))
