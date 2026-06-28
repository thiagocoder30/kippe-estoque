import pytest
from src.domain.product import Product
from src.domain.batch import Batch
from src.domain.cycle_count import CycleCountTask
from src.domain.services.cycle_count_engine import CycleCountEngine
def test_cycle_count_perfect_match():
    p = Product(id="SKU-CC-1", name="Arroz")
    p.batches["L-100"] = Batch(code="L-100", product_id="SKU-CC-1", quantity=50, expiration_date="2030-01-01", warehouse_id="WH-1")
    p.quantity = 50
    
    task = CycleCountTask(id="CC-001", warehouse_id="WH-1", operator_id="OP-01")
    
    # Registra contagem exata
    res1 = CycleCountEngine.register_count(task, "L-100", 50)
    assert res1.is_success is True
    
    res2 = CycleCountEngine.complete_task(task)
    assert res2.is_success is True
    
    res3 = CycleCountEngine.approve_and_reconcile(task, [p], "MGR-01")
    assert res3.is_success is True
    assert p.quantity == 50 # Nenhuma alteração foi necessária
def test_cycle_count_with_shortage_delegates_to_adjustment():
    p = Product(id="SKU-CC-2", name="Feijão")
    p.batches["L-200"] = Batch(code="L-200", product_id="SKU-CC-2", quantity=30, expiration_date="2030-01-01", warehouse_id="WH-1")
    p.quantity = 30
    
    task = CycleCountTask(id="CC-002", warehouse_id="WH-1", operator_id="OP-01")
    
    # Registra falta física (achou apenas 25)
    CycleCountEngine.register_count(task, "L-200", 25)
    CycleCountEngine.complete_task(task)
    
    res = CycleCountEngine.approve_and_reconcile(task, [p], "MGR-01")
    assert res.is_success is True
    assert task.status == "APPROVED"
    # O InventoryAdjustmentEngine deve ter debitado 5
    assert p.batches["L-200"].quantity == 25
    assert p.quantity == 25
def test_cycle_count_with_surplus_delegates_to_adjustment():
    p = Product(id="SKU-CC-3", name="Macarrão")
    p.batches["L-300"] = Batch(code="L-300", product_id="SKU-CC-3", quantity=10, expiration_date="2030-01-01", warehouse_id="WH-1")
    p.quantity = 10
    
    task = CycleCountTask(id="CC-003", warehouse_id="WH-1", operator_id="OP-01")
    
    # Registra sobra física (achou 15)
    CycleCountEngine.register_count(task, "L-300", 15)
    CycleCountEngine.complete_task(task)
    
    CycleCountEngine.approve_and_reconcile(task, [p], "MGR-01")
    assert p.batches["L-300"].quantity == 15
    assert p.quantity == 15
def test_cycle_count_rejects_unauthorized_closure():
    task = CycleCountTask(id="CC-004", warehouse_id="WH-1", operator_id="OP-01")
    
    # Tenta aprovar uma tarefa que está OPEN (não completada)
    res = CycleCountEngine.approve_and_reconcile(task, [], "MGR-01")
    assert res.is_success is False
    assert "A tarefa deve estar CONCLUÍDA antes da aprovação" in res.error
