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
