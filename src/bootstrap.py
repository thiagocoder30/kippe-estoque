from src.infrastructure.persistence.json.purchase_order_repository import JsonPurchaseOrderRepository
from src.infrastructure.persistence.json.supplier_repository import JsonSupplierRepository
from src.infrastructure.observability.ndjson_audit import NDJSONAuditLogger
from src.application.procurement.use_cases import CreatePurchaseOrderUseCase, ApprovePurchaseOrderUseCase
from src.application.middleware.decorators import UseCaseAuditDecorator

class Bootstrap:
    """
    Composition Root Consolidado.
    Monta os Repositórios, os Use Cases Puros e injeta os Decorators Transversais.
    """
    def __init__(self, use_memory: bool = False):
        if use_memory:
            from src.infrastructure.persistence.in_memory.purchase_order_repository import InMemoryPurchaseOrderRepository
            from src.infrastructure.persistence.in_memory.supplier_repository import InMemorySupplierRepository
            self.po_repo = InMemoryPurchaseOrderRepository()
            self.sup_repo = InMemorySupplierRepository()
        else:
            self.po_repo = JsonPurchaseOrderRepository()
            self.sup_repo = JsonSupplierRepository()

        # Portas Transversais (Infra)
        self.audit_port = NDJSONAuditLogger()

        # Instanciação Pura (Core)
        base_create_uc = CreatePurchaseOrderUseCase(self.po_repo, self.sup_repo)
        base_approve_uc = ApprovePurchaseOrderUseCase(self.po_repo)

        # Envolvimento Transversal (Decorators)
        self.create_po_uc = UseCaseAuditDecorator(base_create_uc, "CREATE_PO", self.audit_port)
        self.approve_po_uc = UseCaseAuditDecorator(base_approve_uc, "APPROVE_PO", self.audit_port)

    def get_create_po_use_case(self):
        return self.create_po_uc

    def get_approve_po_use_case(self):
        return self.approve_po_uc
