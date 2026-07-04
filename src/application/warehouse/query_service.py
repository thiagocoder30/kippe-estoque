from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.domain.warehouse import (
    DualStockView, SmartSheetBuilder, ReplenishmentEngine,
    TrustScoreEngine, OperationalTruthEngine, DivergenceEngine
)
from src.domain.warehouse.balance import BalanceEngine
from src.domain.warehouse.topology import TopologyResolver
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
    description: str = "Produto não cadastrado"
    brand: str = "N/A"
    category: str = "N/A"
    physical_zone: str = "N/A"
    physical_details: str = "N/A"

class InventoryQueryService:
    def __init__(self, ledger_repo: InventoryAccountRepository, catalog_repo=None, **kwargs):
        self.ledger_repo = ledger_repo
        self.catalog_repo = catalog_repo or kwargs.get('catalog_repo')

    def get_sku_view(self, sku: str, min_stock: int = 40, ideal_stock: int = 120) -> InventoryProductView:
        account = self.ledger_repo.get_by_sku(sku)
        if not account:
            raise NotFoundException(f"SKU {sku} não possui histórico no Ledger.")

        try:
            sheet = SmartSheetBuilder.build(account, min_stock=min_stock)
        except TypeError:
            sheet = SmartSheetBuilder.build(account)
            
        dual_stock = DualStockView.calculate(account.entries, sku)
        replenishment = ReplenishmentEngine.calculate(sheet, min_stock, ideal_stock)

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

        desc, brand, cat = "Produto não cadastrado", "N/A", "N/A"
        if self.catalog_repo:
            try:
                product = self.catalog_repo.get_by_sku(sku)
                if product:
                    desc = getattr(product, "description", desc)
                    brand = getattr(product, "brand", brand)
                    cat = getattr(product, "category", cat)
            except Exception:
                pass

        # Resolução do Endereço Físico (Topologia)
        address = TopologyResolver.get_physical_address(category=cat, description=desc)

        next_exp = getattr(sheet, "next_to_expire", {}) or {}
        last_rec = getattr(sheet, "last_receipt", {}) or {}

        return InventoryProductView(
            sku=sku,
            available_total=dual_stock["total"],
            depot_balance=dual_stock["depot"],
            store_balance=dual_stock["store"],
            active_batch=next_exp.get("id", "N/A") if isinstance(next_exp, dict) else "N/A",
            primary_supplier=last_rec.get("supplier", "N/A") if isinstance(last_rec, dict) else "N/A",
            last_receipt_date=last_rec.get("date", "N/A") if isinstance(last_rec, dict) else "N/A",
            first_expiration_date=next_exp.get("expiration", "N/A") if isinstance(next_exp, dict) else "N/A",
            min_stock=min_stock,
            ideal_stock=ideal_stock,
            replenishment_needed=(replenishment is not None),
            suggested_quantity=getattr(replenishment, "suggested_quantity", getattr(replenishment, "quantity", 0)) if replenishment else 0,
            trust_score_percentage=int(trust.score * 100),
            divergence_count=trust.divergence_count,
            last_divergence=last_div_desc,
            operational_risk=round((1.0 - trust.score) * 0.4 + (1.0 - trust.score) * 0.4, 2),
            recommended_action=getattr(insight, "suggested_action", "OK"),
            action_priority=getattr(insight, "priority", "NORMAL"),
            description=desc,
            brand=brand,
            category=cat,
            physical_zone=address.zone,
            physical_details=address.details
        )

