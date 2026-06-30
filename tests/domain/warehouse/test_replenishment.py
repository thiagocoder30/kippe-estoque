import pytest
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.domain.warehouse.smart_sheet import SmartSheetBuilder
from src.domain.warehouse.replenishment import ReplenishmentEngine
from src.security.exceptions import BusinessRuleViolation

def create_mock_sheet(sku: str, qty: int) -> "SkuSmartSheet":
    account = InventoryAccount(sku=sku)
    if qty > 0:
        account.record_transaction("L1", TransactionType.GOODS_RECEIPT, qty, "A1", "NF-1")
    elif qty < 0:
        # Força saldo negativo para teste de rutura
        account.record_transaction("L1", TransactionType.GOODS_RECEIPT, 1, "A1", "NF-1")
        account.record_transaction("L1", TransactionType.SALE, -abs(qty)-1, "A1", "PED-1")
    return SmartSheetBuilder.build(account)

def test_replenishment_engine_suggests_normal_purchase():
    # Saldo 8, Minimo 10, Ideal 50 -> Sugere comprar 42
    sheet = create_mock_sheet("DETERGENTE", 8)
    suggestion = ReplenishmentEngine.calculate(sheet, min_stock=10, ideal_stock=50)
    
    assert suggestion is not None
    assert suggestion.suggested_quantity == 42
    assert suggestion.urgency == "NORMAL"

def test_replenishment_engine_suggests_high_urgency():
    # Saldo 4, Minimo 10 (saldo <= 50% do mínimo)
    sheet = create_mock_sheet("CAFE", 4)
    suggestion = ReplenishmentEngine.calculate(sheet, min_stock=10, ideal_stock=30)
    
    assert suggestion.urgency == "HIGH"
    assert suggestion.suggested_quantity == 26

def test_replenishment_engine_suggests_critical_urgency_on_stockout():
    # Saldo 0 ou negativo
    sheet = create_mock_sheet("SABAO", 0)
    suggestion = ReplenishmentEngine.calculate(sheet, min_stock=5, ideal_stock=20)
    
    assert suggestion.urgency == "CRITICAL"
    assert suggestion.suggested_quantity == 20

def test_replenishment_engine_ignores_healthy_stock():
    # Saldo 15, Mínimo 10 -> Nenhuma sugestão
    sheet = create_mock_sheet("LEITE", 15)
    suggestion = ReplenishmentEngine.calculate(sheet, min_stock=10, ideal_stock=50)
    
    assert suggestion is None

def test_replenishment_engine_validates_parameters():
    sheet = create_mock_sheet("TESTE", 5)
    
    with pytest.raises(BusinessRuleViolation, match="maior que o estoque mínimo"):
        ReplenishmentEngine.calculate(sheet, min_stock=10, ideal_stock=10)
        
    with pytest.raises(BusinessRuleViolation, match="não podem ser negativos"):
        ReplenishmentEngine.calculate(sheet, min_stock=-5, ideal_stock=20)
