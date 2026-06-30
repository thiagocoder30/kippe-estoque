import pytest
from src.domain.procurement.analytics import ProcurementAnalyticsEngine, ProcurementDashboard
from src.domain.procurement.ledger import SupplierLedger
from src.domain.procurement.three_way_match import MatchResult
from src.domain.procurement.performance import SupplierPerformance

def test_procurement_analytics_dashboard_generation():
    # 1. Configurando Mock do Ledger com Timestamps Manipulados para Teste
    ledger = SupplierLedger()
    
    # Pedido 1: Criado -> Aprovado (2h) -> Recebido (24h após aprovação)
    e1 = ledger.append_event("EV-1", "PurchaseOrderCreated", "PO-1", {})
    object.__setattr__(e1, 'timestamp', "2026-06-01 10:00:00") # Burlar Frozen para mock
    e2 = ledger.append_event("EV-2", "PurchaseApproved", "PO-1", {})
    object.__setattr__(e2, 'timestamp', "2026-06-01 12:00:00")
    e3 = ledger.append_event("EV-3", "GoodsReceived", "PO-1", {})
    object.__setattr__(e3, 'timestamp', "2026-06-02 12:00:00")
    
    # Pedido 2: Criado -> Aprovado (4h), ainda pendente de recebimento
    e4 = ledger.append_event("EV-4", "PurchaseOrderCreated", "PO-2", {})
    object.__setattr__(e4, 'timestamp', "2026-06-05 08:00:00")
    e5 = ledger.append_event("EV-5", "PurchaseApproved", "PO-2", {})
    object.__setattr__(e5, 'timestamp', "2026-06-05 12:00:00")

    # 2. Configurando Mock do Three-Way Match (75% de sucesso)
    matches = [
        MatchResult(is_matched=True),
        MatchResult(is_matched=True),
        MatchResult(is_matched=True),
        MatchResult(is_matched=False, divergences=["Price"], quantity_delta={}, price_delta={"SKU-1": 10.0})
    ]

    # 3. Configurando Mock de Fornecedores
    perfs = [
        SupplierPerformance("SUP-1", 90.0, 90.0, 90.0, 90.0, 90.0),
        SupplierPerformance("SUP-2", 80.0, 80.0, 80.0, 80.0, 80.0),
        SupplierPerformance("SUP-3", 100.0, 100.0, 100.0, 100.0, 100.0), # Top 1
        SupplierPerformance("SUP-4", 50.0, 50.0, 50.0, 50.0, 50.0)       # Bottom 1
    ]

    # 4. Geração do Dashboard
    dashboard = ProcurementAnalyticsEngine.generate_dashboard(
        ledger=ledger,
        match_results=matches,
        performances=perfs
    )

    # 5. Asserções do Motor Analítico
    assert dashboard.total_purchase_orders_created == 2
    assert dashboard.three_way_match_success_rate == 75.0
    assert dashboard.avg_approval_time_hours == 3.0 # (2h + 4h) / 2
    assert dashboard.avg_receipt_time_hours == 24.0 # Somente o PO-1 foi recebido
    
    assert dashboard.top_suppliers[0].supplier_id == "SUP-3"
    assert dashboard.bottom_suppliers[-1].supplier_id == "SUP-4"
