#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E016.3: API ERROR VISIBILITY & DOMAIN HARDENING
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=3
kippe::banner_program "E" "E016.3" "API Error Visibility & Domain Hardening"

kippe::step 1 ${TOTAL_STEPS} "Hardening SmartSheetBuilder against NoneTypes in Metadata..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/smart_sheet.py"
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.domain.warehouse.balance import BalanceEngine

@dataclass
class SkuSmartSheet:
    sku: str
    total_balance: int
    reserved_balance: int
    available_balance: int
    locations: Dict[str, int]
    batches: List[Dict[str, Any]]
    next_to_expire: Optional[Dict[str, Any]]
    last_receipt: Optional[Dict[str, Any]]
    recent_history: List[Dict[str, Any]]
    alerts: List[str]

class SmartSheetBuilder:
    @staticmethod
    def build(account: InventoryAccount, reserved_qty: int = 0, min_stock: int = 10) -> SkuSmartSheet:
        projection = BalanceEngine.calculate(account)
        
        sorted_entries = sorted(account.entries, key=lambda e: e.timestamp, reverse=True)
        recent_history = [{"date": e.timestamp[:10], "type": e.transaction_type.value, "qty": e.quantity, "loc": e.location_id} for e in sorted_entries[:5]]
        
        last_receipt = None
        for e in sorted_entries:
            if e.transaction_type == TransactionType.GOODS_RECEIPT:
                last_receipt = {
                    "date": e.timestamp[:10],
                    "supplier": e.metadata.get("supplier", "Desconhecido"),
                    "nf": e.reference_document,
                    "qty": e.quantity
                }
                break

        batch_details = {}
        for e in account.entries:
            if e.batch_id not in batch_details:
                batch_details[e.batch_id] = {"id": e.batch_id, "qty": 0, "expiration": "9999-12-31"}
            batch_details[e.batch_id]["qty"] += e.quantity
            
            # Defesa contra dicionários com "expiration_date": None
            if "expiration_date" in e.metadata and e.metadata["expiration_date"]:
                batch_details[e.batch_id]["expiration"] = e.metadata["expiration_date"]

        active_batches = [b for b in batch_details.values() if b["qty"] > 0]
        active_batches.sort(key=lambda b: b["expiration"] or "9999-12-31")
        
        next_to_expire = active_batches[0] if active_batches else None
        
        alerts = []
        available = projection.total - reserved_qty
        
        if available < min_stock:
            alerts.append(f"⚠ Saldo disponível ({available}) abaixo do mínimo ({min_stock})")
        if len(active_batches) == 1:
            alerts.append("⚠ Lote único em stock")
            
        # Defesa contra falhas no parse de datas sujas
        if next_to_expire and next_to_expire["expiration"] not in (None, "9999-12-31", "UNKNOWN"):
            try:
                days_to_expire = (datetime.strptime(next_to_expire["expiration"], "%Y-%m-%d") - datetime.now()).days
                if days_to_expire < 30:
                    alerts.append(f"⚠ Lote {next_to_expire['id']} vence em {days_to_expire} dias")
            except (ValueError, TypeError):
                pass # Ignora falhas de parse de forma silenciosa para não derrubar a view

        return SkuSmartSheet(
            sku=account.sku, total_balance=projection.total, reserved_balance=reserved_qty,
            available_balance=available, locations=projection.by_location, batches=active_batches,
            next_to_expire=next_to_expire, last_receipt=last_receipt,
            recent_history=recent_history, alerts=alerts
        )
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Removing the Muzzle: Adding Tracebacks to API Router..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/presentation/api/warehouse_router.py"
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
            # Nunca engolir exceções em modo desenvolvimento
            print("\n\033[91m[API INTERNAL ERROR]\033[0m")
            traceback.print_exc()
            return 500, {"error": "Erro interno do servidor.", "details": str(e)}

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
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Platform Regression..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "115" "1.5.0-platform" "E016.3" "SUCCESS"

echo -e "\n[STATUS] API Router Tracebacks ativados e SmartSheetBuilder blindado com sucesso!"
exit 0

