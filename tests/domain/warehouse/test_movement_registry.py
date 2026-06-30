import pytest
from src.domain.warehouse.movement import MovementEngine, DualStockView
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.security.exceptions import BusinessRuleViolation

def test_movement_engine_registers_fast_event():
    event = MovementEngine.register(
        sku="DETERGENTE-X", quantity=6, movement_type="TO_STORE",
        origin="REPOSITOR_APP", destination="STORE"
    )
    assert event.sku == "DETERGENTE-X"
    assert event.quantity == 6

def test_dual_stock_view_calculates_partitions_from_ledger():
    account = InventoryAccount(sku="DETERGENTE-X")
    
    # 1. Base inicial no depósito (Goods Receipt)
    account.record_transaction("L1", TransactionType.GOODS_RECEIPT, 100, "DEPOT", "NF-1")
    
    # 2. Transferência para a loja (10 un)
    account.record_transaction("L1", TransactionType.TRANSFER_OUT, -10, "DEPOT", "APP")
    account.record_transaction("L1", TransactionType.TRANSFER_IN, 10, "STORE", "APP")
    
    # 3. Transferência para a loja (2 un)
    account.record_transaction("L1", TransactionType.TRANSFER_OUT, -2, "DEPOT", "APP")
    account.record_transaction("L1", TransactionType.TRANSFER_IN, 2, "STORE", "APP")
    
    # 4. Consumo na Loja (Venda PDV: 3 un)
    account.record_transaction("L1", TransactionType.SALE, -3, "STORE", "PDV")
    
    view = DualStockView.calculate(account.entries, sku="DETERGENTE-X")
    
    assert view["depot"] == 88  # 100 - 10 - 2
    assert view["store"] == 9   # 10 + 2 - 3
    assert view["total"] == 97  # 88 + 9

def test_movement_engine_prevents_zero_quantity():
    with pytest.raises(BusinessRuleViolation, match="estritamente positiva"):
        MovementEngine.register("SKU-1", 0, "TO_STORE", "APP", "STORE")
