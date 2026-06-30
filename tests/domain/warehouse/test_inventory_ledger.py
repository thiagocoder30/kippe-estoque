import pytest
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.security.exceptions import BusinessRuleViolation

def test_inventory_account_records_receipt_correctly():
    account = InventoryAccount(sku="SKU-789")
    
    entry = account.record_transaction(
        batch_id="L240601",
        tx_type=TransactionType.GOODS_RECEIPT,
        quantity=24,
        location_id="C2",
        reference_document="PO-00034"
    )
    
    assert len(account.entries) == 1
    assert entry.quantity == 24
    assert entry.transaction_type == TransactionType.GOODS_RECEIPT
    assert entry.location_id == "C2"

def test_inventory_account_enforces_negative_quantity_for_sales():
    account = InventoryAccount(sku="SKU-789")
    
    with pytest.raises(BusinessRuleViolation, match="exigem quantidades negativas"):
        account.record_transaction(
            batch_id="L240601",
            tx_type=TransactionType.SALE,
            quantity=5, # Erro: Venda deve ser negativa (-5)
            location_id="C2",
            reference_document="INV-999"
        )
        
    # Validando o caso correto
    entry = account.record_transaction("L240601", TransactionType.SALE, -5, "C2", "INV-999")
    assert entry.quantity == -5

def test_inventory_account_prevents_zero_quantity():
    account = InventoryAccount(sku="SKU-789")
    with pytest.raises(BusinessRuleViolation, match="não pode ser zero"):
        account.record_transaction("L1", TransactionType.ADJUSTMENT, 0, "A1", "ADJ-1")
