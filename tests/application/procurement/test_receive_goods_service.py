import pytest
from src.domain.procurement.order import PurchaseOrder
from src.domain.product import Product
from src.application.procurement.receive_goods_service import ReceiveGoodsCommand, ReceiveGoodsService

def test_application_service_orchestrates_procurement_and_inventory():
    # 1. Configuração do Mock de Inventário (Core Frozen)
    p1 = Product(id="SKU-GR-1", name="Placa de Video", quantity=0)
    catalog = {"SKU-GR-1": p1}
    
    # 2. Configuração do Pedido de Compras
    order = PurchaseOrder(id="PO-2001", supplier_id="SUP-MASTER")
    order.add_item(sku="SKU-GR-1", quantity=50, unit_price=2500.0)
    order.submit()
    order.start_approval()
    order.approve()
    order.place_order()
    
    # 3. Comando de Aplicação
    cmd = ReceiveGoodsCommand(
        order_id="PO-2001",
        items_received={"SKU-GR-1": 50},
        warehouse_id="CD-SUL",
        operator_id="OP-RECEBIMENTO"
    )
    
    # 4. Execução do Serviço
    ReceiveGoodsService.execute(command=cmd, order=order, inventory_catalog=catalog)
    
    # 5. Asserções (Contratos Respeitados em ambos os Bounded Contexts)
    assert order.status == "RECEIVED"
    assert p1.quantity == 50
    
    # Verifica se o lote foi fisicamente criado no Inventário com os atributos da Compra
    batches = list(p1.batches.values())
    assert len(batches) == 1
    batch = batches[0]
    
    assert batch.product_id == "SKU-GR-1"
    assert batch.quantity == 50
    assert batch.cost_per_unit == 2500.0
    assert batch.supplier == "SUP-MASTER"
    assert batch.code.startswith("GR-PO-2001-SKU-GR-1-")
