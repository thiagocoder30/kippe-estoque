from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.domain.warehouse import (
    DualStockView, SmartSheetBuilder, ReplenishmentEngine, 
    TrustScoreEngine, OperationalTruthEngine, DivergenceEngine
)
from src.security.exceptions import NotFoundException

@dataclass(frozen=True)
class InventoryProductView:
    sku: str
    available_total: int
    depot_balance: int
    store_balance: int
    active_batch: Optional[str]
    primary_supplier: Optional[str]
    last_receipt_date: Optional[str]
    first_expiration_date: Optional[str]
    min_stock: int
    ideal_stock: int
    replenishment_needed: bool
    suggested_quantity: int
    trust_score_percentage: int
    divergence_count: int
    last_divergence: Optional[str]
    operational_risk: float
    recommended_action: str
    action_priority: str

class InventoryQueryService:
    def __init__(self, ledger_repo: InventoryAccountRepository):
        self.ledger_repo = ledger_repo

    def get_sku_view(self, sku: str, min_stock: int = 40, ideal_stock: int = 120) -> InventoryProductView:
        account = self.ledger_repo.get_by_sku(sku)
        if not account:
            raise NotFoundException(f"SKU {sku} não possui histórico no Ledger.")

        sheet = SmartSheetBuilder.build(account, min_stock=min_stock)
        dual_stock = DualStockView.calculate(account.entries, sku)
        replenishment = ReplenishmentEngine.calculate(sheet, min_stock, ideal_stock)
        
        # O Domínio agora reconstrói a sua própria realidade
        div_events = DivergenceEngine.extract_from_ledger(account.entries)
        trust = TrustScoreEngine.calculate(div_events)
        
        insight = OperationalTruthEngine.evaluate(
            sku=sku,
            stock_total=dual_stock["total"],
            divergence_penalty=(1.0 - trust.score),
            trust_score=trust.score,
            inbound_risk=0.0
        )

        last_div = div_events[-1] if div_events else None
        last_div_desc = f"{last_div.divergence_type} ({last_div.delta} un)" if last_div else "Nenhuma"

        return InventoryProductView(
            sku=sku,
            available_total=dual_stock["total"],
            depot_balance=dual_stock["depot"],
            store_balance=dual_stock["store"],
            active_batch=sheet.next_to_expire["id"] if sheet.next_to_expire else "N/A",
            primary_supplier=sheet.last_receipt["supplier"] if sheet.last_receipt else "N/A",
            last_receipt_date=sheet.last_receipt["date"] if sheet.last_receipt else "N/A",
            first_expiration_date=sheet.next_to_expire["expiration"] if sheet.next_to_expire else "N/A",
            min_stock=min_stock,
            ideal_stock=ideal_stock,
            replenishment_needed=(replenishment is not None),
            suggested_quantity=replenishment.suggested_quantity if replenishment else 0,
            trust_score_percentage=int(trust.score * 100),
            divergence_count=trust.divergence_count,
            last_divergence=last_div_desc,
            operational_risk=round((1.0 - trust.score) * 0.4 + (1.0 - trust.score) * 0.4, 2),
            recommended_action=insight.suggested_action,
            action_priority=insight.priority
        )
