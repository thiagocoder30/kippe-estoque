import json
import traceback
from typing import Dict, Any, Tuple
from src.application.warehouse.command_bus import CommandBus
from src.application.warehouse.query_service import InventoryQueryService
from src.application.warehouse.commands import (
    ReceiveGoodsCommand, TransferToStoreCommand, RegisterAdjustmentCommand
)
from src.security.exceptions import NotFoundException, BusinessRuleViolation

class WarehouseAPIRouter:
    def __init__(self, query_service: InventoryQueryService, command_bus: CommandBus):
        self.query_service = query_service
        self.command_bus = command_bus

    # ==========================================
    # READ SIDE (GET)
    # ==========================================
    
    def get_sku(self, sku: str) -> Tuple[int, Dict[str, Any]]:
        try:
            view = self.query_service.get_sku_view(sku)
            return 200, {
                "sku": view.sku,
                "description": view.description,
                "balances": {
                    "total": view.available_total,
                    "depot": view.depot_balance,
                    "store": view.store_balance
                },
                "operational_metrics": {
                    "trust_score": view.trust_score_percentage,
                    "risk_level": view.action_priority,
                    "recommended_action": view.recommended_action
                }
            }
        except NotFoundException as e:
            return 404, {"error": str(e)}
        except Exception as e:
            print("\n\033[91m[API INTERNAL ERROR]\033[0m")
            traceback.print_exc()
            return 500, {"error": "Erro interno do servidor.", "details": str(e)}

    # ==========================================
    # WRITE SIDE (POST)
    # ==========================================

    def post_receive_goods(self, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        try:
            cmd = ReceiveGoodsCommand(
                sku=payload["sku"], quantity=payload["quantity"], supplier=payload["supplier"],
                batch_code=payload["batch_code"], expiration_date=payload.get("expiration_date"),
                invoice_id=payload.get("invoice_id"), operator=payload["operator"]
            )
            self.command_bus.dispatch(cmd)
            return 201, {"message": "Recebimento registado com sucesso."}
        except KeyError as e:
            return 400, {"error": f"Campo obrigatório ausente: {str(e)}"}
        except NotFoundException as e:
            return 404, {"error": str(e)}
        except BusinessRuleViolation as e:
            return 422, {"error": str(e)}
        except Exception as e:
            print("\n\033[91m[API INTERNAL ERROR]\033[0m")
            traceback.print_exc()
            return 500, {"error": "Erro interno do servidor."}

    def post_transfer_to_store(self, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        try:
            cmd = TransferToStoreCommand(
                sku=payload["sku"], quantity=payload["quantity"],
                batch_code=payload["batch_code"], operator=payload["operator"]
            )
            self.command_bus.dispatch(cmd)
            return 201, {"message": "Transferência para loja registada."}
        except Exception as e:
            return 400, {"error": str(e)}

    def post_register_adjustment(self, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        try:
            cmd = RegisterAdjustmentCommand(
                sku=payload["sku"], quantity=payload["quantity"],
                batch_code=payload["batch_code"], divergence_type=payload["divergence_type"],
                reason=payload["reason"], operator=payload["operator"]
            )
            self.command_bus.dispatch(cmd)
            return 201, {"message": "Divergência/Ajuste registado com sucesso."}
        except Exception as e:
            return 400, {"error": str(e)}
