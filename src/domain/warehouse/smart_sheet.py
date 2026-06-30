from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.domain.warehouse.balance import BalanceEngine

@dataclass
class SkuSmartSheet:
    """
    Read Model ultra-otimizado para a operação (Ficha Inteligente).
    Responde a todas as perguntas críticas num único ecrã.
    """
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
    """Projeta a Ficha Inteligente varrendo o Ledger de forma otimizada."""
    @staticmethod
    def build(account: InventoryAccount, reserved_qty: int = 0, min_stock: int = 10) -> SkuSmartSheet:
        # 1. Saldo e Localizações (Reutiliza o BalanceEngine E004)
        projection = BalanceEngine.calculate(account)
        
        # 2. Histórico e Recebimentos
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

        # 3. Lotes e Validades (Motor FEFO Base)
        batch_details = {}
        for e in account.entries:
            if e.batch_id not in batch_details:
                batch_details[e.batch_id] = {"id": e.batch_id, "qty": 0, "expiration": e.metadata.get("expiration_date", "9999-12-31")}
            batch_details[e.batch_id]["qty"] += e.quantity
            # Atualiza validade se foi informada num recebimento posterior
            if "expiration_date" in e.metadata:
                batch_details[e.batch_id]["expiration"] = e.metadata["expiration_date"]

        active_batches = [b for b in batch_details.values() if b["qty"] > 0]
        # Ordenação FEFO (First Expire, First Out)
        active_batches.sort(key=lambda b: b["expiration"])
        
        next_to_expire = active_batches[0] if active_batches else None
        
        # 4. Alertas Inteligentes
        alerts = []
        available = projection.total - reserved_qty
        
        if available < min_stock:
            alerts.append(f"⚠ Saldo disponível ({available}) abaixo do mínimo ({min_stock})")
        if len(active_batches) == 1:
            alerts.append("⚠ Lote único em stock")
        if next_to_expire and next_to_expire["expiration"] != "9999-12-31":
            days_to_expire = (datetime.strptime(next_to_expire["expiration"], "%Y-%m-%d") - datetime.now()).days
            if days_to_expire < 30:
                alerts.append(f"⚠ Lote {next_to_expire['id']} vence em {days_to_expire} dias")

        return SkuSmartSheet(
            sku=account.sku,
            total_balance=projection.total,
            reserved_balance=reserved_qty,
            available_balance=available,
            locations=projection.by_location,
            batches=active_batches,
            next_to_expire=next_to_expire,
            last_receipt=last_receipt,
            recent_history=recent_history,
            alerts=alerts
        )
