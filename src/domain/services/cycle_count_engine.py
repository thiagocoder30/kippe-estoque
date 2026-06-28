from typing import List
from src.domain.product import Product
from src.domain.cycle_count import CycleCountTask
from src.domain.result import Result
from src.domain.services.inventory_adjustment_engine import InventoryAdjustmentEngine
class CycleCountEngine:
    """
    Domain Service: CycleCountEngine
    Gerencia a descoberta de divergências físicas.
    Delega a aplicação de correções ao InventoryAdjustmentEngine mediante aprovação.
    """
    @staticmethod
    def register_count(task: CycleCountTask, batch_code: str, quantity: int) -> Result[None, str]:
        if task.status not in ["OPEN", "IN_PROGRESS"]:
            return Result.fail(f"Não é possível registrar contagens em uma tarefa com status {task.status}.")
        if quantity < 0:
            return Result.fail("A quantidade contada não pode ser negativa.")
            
        task.status = "IN_PROGRESS"
        task.counted_items[batch_code] = quantity
        return Result.ok(None)
    @staticmethod
    def complete_task(task: CycleCountTask) -> Result[None, str]:
        if task.status != "IN_PROGRESS":
            return Result.fail("Apenas tarefas EM ANDAMENTO podem ser marcadas como concluídas.")
        task.status = "COMPLETED"
        return Result.ok(None)
    @staticmethod
    def approve_and_reconcile(task: CycleCountTask, products: List[Product], approver_id: str) -> Result[None, str]:
        if task.status != "COMPLETED":
            return Result.fail("A tarefa deve estar CONCLUÍDA antes da aprovação gerencial.")
        if not approver_id:
            return Result.fail("O ID do Aprovador é obrigatório para trilha de auditoria.")
        # Reconciliação Física vs Sistêmica
        for product in products:
            for batch_code, counted_qty in task.counted_items.items():
                if batch_code in product.batches:
                    system_qty = product.batches[batch_code].quantity
                    difference = counted_qty - system_qty
                    
                    if difference != 0:
                        reason = "SOBRA" if difference > 0 else "PERDA"
                        
                        # Delegação arquitetural para o motor de ajustes consolidado na INV010
                        adj_res = InventoryAdjustmentEngine.execute_adjustment(
                            product=product,
                            amount=difference,
                            reason=reason,
                            operator_id=approver_id,
                            warehouse_id=task.warehouse_id,
                            batch_code=batch_code
                        )
                        if not adj_res.is_success:
                            return Result.fail(f"Falha de conciliação no lote {batch_code}: {adj_res.error}")
        task.status = "APPROVED"
        task.approved_by = approver_id
        return Result.ok(None)
