from src.infrastructure.persistence.json.purchase_order_repository import JsonPurchaseOrderRepository
from src.infrastructure.persistence.json.supplier_repository import JsonSupplierRepository
from src.application.procurement.use_cases import CreatePurchaseOrderUseCase, ApprovePurchaseOrderUseCase

class Bootstrap:
    """
    Composition Root: Instancia a Aplicação.
    Centraliza a Injeção de Dependências (DI). 
    A Camada de Apresentação utiliza o Bootstrap para obter os Casos de Uso
    sem precisar conhecer as implementações de Infraestrutura.
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

        # Injeção de Casos de Uso (Application Layer)
        self.create_po_uc = CreatePurchaseOrderUseCase(self.po_repo, self.sup_repo)
        self.approve_po_uc = ApprovePurchaseOrderUseCase(self.po_repo)

    def get_create_po_use_case(self) -> CreatePurchaseOrderUseCase:
        return self.create_po_uc

    def get_approve_po_use_case(self) -> ApprovePurchaseOrderUseCase:
        return self.approve_po_uc
