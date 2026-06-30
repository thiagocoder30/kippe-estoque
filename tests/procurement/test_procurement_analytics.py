import pytest
from src.domain.procurement.analytics import ProcurementAnalyticsEngine, ProcurementDashboard
from src.domain.procurement.ledger import SupplierLedger
from src.domain.procurement.three_way_match import MatchResult
from src.domain.procurement.performance import SupplierPerformance
from src.domain.procurement.settlement import InvoiceSettlement, PaymentTerms
from src.domain.procurement.order import MonetaryValue

def test_procurement_analytics_extended_dashboard_metrics():
    # 1. Configurando Histórico Cronológico do Ledger
    ledger = SupplierLedger()
    
    e1 = ledger.append_event("EV-1", "PurchaseOrderCreated", "PO-1", {})
    object.__setattr__(e1, 'timestamp', "2026-06-01 10:00:00")
    e2 = ledger.append_event("EV-2", "PurchaseApproved", "PO-1", {})
    object.__setattr__(e2, 'timestamp', "2026-06-01 12:00:00")
    e3 = ledger.append_event("EV-3", "GoodsReceived", "PO-1", {})
    object.__setattr__(e3, 'timestamp', "2026-06-02 12:00:00")

    # 2. Configurando Resultados do Match (Com divergências financeiras capturadas)
    matches = [
        MatchResult(is_matched=True),
        MatchResult(is_matched=False, divergences=["Preço Maior"], quantity_delta={}, price_delta={"SKU-MOCK": 150.50})
    ]

    # 3. Configurando Amostras de Performance
    perfs = [
        SupplierPerformance("SUP-1", 100.0, 100.0, 100.0, 100.0, 100.0),
        SupplierPerformance("SUP-2", 40.0, 40.0, 40.0, 40.0, 40.0)
    ]

    # 4. Configurando Liquidações de Fatura para Medição de Adimplemento (D010)
    terms = PaymentTerms(description="Net 30", due_days=30)
    s1 = InvoiceSettlement("SET-1", "NF-1", "PO-1", MonetaryValue(100.0), terms, status="PAID")
    
    # Processamento Analítico Extensivo
    dashboard = ProcurementAnalyticsEngine.generate_dashboard(
        ledger=ledger,
        match_results=matches,
        performances=perfs,
        settlements=[s1]
    )

    # 5. Validação das Invariantes do Motor de Inteligência Expandido
    assert dashboard.total_purchase_orders_created == 1
    assert dashboard.three_way_match_success_rate == 50.0
    assert dashboard.first_pass_match_rate == 50.0
    assert dashboard.price_variance_amount == 150.50
    assert dashboard.payment_compliance_rate == 100.0
    assert dashboard.top_suppliers[0].supplier_id == "SUP-1"
