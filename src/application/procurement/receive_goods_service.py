from dataclasses import dataclass
from typing import Dict
from datetime import datetime
from src.domain.procurement.order import PurchaseOrder
from src.domain.product import Product
from src.domain.batch import Batch

@dataclass
class ReceiveGoodsCommand:
    order_id: str
    items_received: Dict[str, int]
    warehouse_id: str
    operator_id: str
    # Utilizado para simplificar o preenchimento da data de expiração no mock E2E
    expiration_date: str = "2099-12-31" 

class ReceiveGoodsService:
    """
    Application Service: Orquestra a transição de estado no Domínio de Compras
    e interage com o Contrato Público do Domínio de Inventário (Baseline 1.3.0 Frozen).
    """
    @staticmethod
    def execute(command: ReceiveGoodsCommand, order: PurchaseOrder, inventory_catalog: Dict[str, Product]) -> None:
        if order.id != command.order_id:
            raise ValueError("Inconsistência: O comando não corresponde ao pedido fornecido.")
            
        for sku, qty in command.items_received.items():
            if qty <= 0:
                raise ValueError(f"Quantidade de recebimento inválida para o SKU {sku}.")

            # 1. Atualiza Domínio de Procurement (Máquina de Estados)
            order.receive_item(sku, qty)
            
            # Recupera a linha para extrair o custo financeiro unitário negociado
            line = next(item for item in order.items if item.sku == sku)
            
            # 2. Interage com Domínio de Inventário (Criando o Lote)
            product = inventory_catalog.get(sku)
            if not product:
                raise ValueError(f"Falha de Integração: SKU {sku} não encontrado no catálogo de inventário.")
                
            batch_code = f"GR-{order.id}-{sku}-{datetime.now().strftime('%H%M%S')}"
            
            # Utiliza o contrato estrito consolidado na Sprint INF008
            new_batch = Batch(
                code=batch_code,
                product_id=sku,
                quantity=qty,
                expiration_date=command.expiration_date,
                cost_per_unit=line.unit_price.amount,
                warehouse_id=command.warehouse_id,
                supplier=order.supplier_id
            )
            
            product.batches[batch_code] = new_batch
            product.quantity += qty
