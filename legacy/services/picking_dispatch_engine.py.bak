from src.domain.order import OutboundOrder
from src.domain.result import Result
import uuid
class PickingDispatchEngine:
    """
    Domain Service: PickingDispatchEngine
    Controla o avanço operacional da separação física até a expedição e geração de rastreio.
    """
    @staticmethod
    def start_picking(order: OutboundOrder) -> Result[None, str]:
        if order.status != "ALLOCATED":
            return Result.fail("Operação rejeitada: Apenas pedidos ALOCADOS podem iniciar a separação física (Picking).")
        
        order.status = "PICKING"
        return Result.ok(None)
    @staticmethod
    def confirm_dispatch(order: OutboundOrder) -> Result[str, str]:
        if order.status != "PICKING":
            return Result.fail("Operação rejeitada: O pedido deve estar em SEPARAÇÃO (PICKING) para ser expedido.")
        
        order.status = "DISPATCHED"
        # Gera um código de rastreio corporativo único para a doca de saída
        order.tracking_code = f"TRK-{order.warehouse_id}-{uuid.uuid4().hex[:8].upper()}"
        
        return Result.ok(order.tracking_code)
