from typing import Dict, Any
from src.domain.procurement.order import PurchaseOrder
from src.domain.procurement.repository import PurchaseOrderRepository
from src.domain.procurement.supplier_repository import SupplierRepository

class CreatePurchaseOrderUseCase:
    """Caso de uso para a criação de um novo Pedido de Compra."""
    def __init__(self, po_repo: PurchaseOrderRepository, sup_repo: SupplierRepository):
        self.po_repo = po_repo
        self.sup_repo = sup_repo

    def execute(self, order_id: str, supplier_id: str, items: list[Dict[str, Any]]) -> PurchaseOrder:
        # 1. Validação cruzada com o repositório de fornecedores
        supplier = self.sup_repo.get_by_id(supplier_id)
        if not supplier:
            raise ValueError(f"Fornecedor {supplier_id} não encontrado.")
            
        if supplier.status != "ACTIVE":
            raise ValueError(f"Fornecedor {supplier_id} não está ativo para novas compras.")

        # 2. Criação do Agregado (A regra de negócio habita o Domínio)
        order = PurchaseOrder(id=order_id, supplier_id=supplier_id)
        
        for item in items:
            order.add_item(
                sku=item["sku"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                discount=item.get("discount", 0.0),
                tax=item.get("tax", 0.0)
            )

        # 3. Persistência
        self.po_repo.save(order)
        return order

class ApprovePurchaseOrderUseCase:
    """Caso de uso para aprovação de Pedidos de Compra."""
    def __init__(self, po_repo: PurchaseOrderRepository):
        self.po_repo = po_repo

    def execute(self, order_id: str) -> None:
        order = self.po_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Pedido {order_id} não encontrado.")

        # Delegação do Workflow para o Domínio
        order.approve()
        
        # Persistência do novo estado
        self.po_repo.save(order)
