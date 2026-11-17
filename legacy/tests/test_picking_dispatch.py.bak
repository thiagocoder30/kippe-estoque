import pytest
from src.domain.order import OutboundOrder
from src.domain.services.picking_dispatch_engine import PickingDispatchEngine
def test_picking_and_dispatch_lifecycle():
    order = OutboundOrder(
        id="OUT-001", warehouse_id="WH-SP", operator_id="OP-99", 
        allocated_items={"SKU-A": 10, "SKU-B": 5}
    )
    
    assert order.status == "ALLOCATED"
    
    # Inicia Separação
    res1 = PickingDispatchEngine.start_picking(order)
    assert res1.is_success is True
    assert order.status == "PICKING"
    
    # Confirma Expedição
    res2 = PickingDispatchEngine.confirm_dispatch(order)
    assert res2.is_success is True
    assert order.status == "DISPATCHED"
    assert order.tracking_code.startswith("TRK-WH-SP-")
    assert len(order.tracking_code) > 10
def test_dispatch_fails_if_picking_not_started():
    order = OutboundOrder(
        id="OUT-002", warehouse_id="WH-RJ", operator_id="OP-99", 
        allocated_items={"SKU-C": 2}
    )
    
    # Tenta expedir sem passar pela separação
    res = PickingDispatchEngine.confirm_dispatch(order)
    assert res.is_success is False
    assert "deve estar em SEPARAÇÃO" in res.error
def test_start_picking_fails_if_already_dispatched():
    order = OutboundOrder(
        id="OUT-003", warehouse_id="WH-MG", operator_id="OP-99", 
        allocated_items={"SKU-D": 1}, status="DISPATCHED"
    )
    
    res = PickingDispatchEngine.start_picking(order)
    assert res.is_success is False
    assert "Apenas pedidos ALOCADOS" in res.error
