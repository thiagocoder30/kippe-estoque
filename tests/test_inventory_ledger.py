import pytest
from dataclasses import FrozenInstanceError
from src.domain.ledger import LedgerEntry
def test_ledger_entry_is_immutable():
    entry = LedgerEntry(
        id="TX-001", product_id="SKU-1", event_type="IN",
        quantity_change=10, quantity_before=0, quantity_after=10,
        warehouse_id="WH-1", batch_code="L-1", operator_id="OP-1"
    )
    
    # Valida o bloqueio arquitetural contra alteração retroativa
    with pytest.raises(FrozenInstanceError):
        entry.quantity_change = 20
def test_ledger_entry_validates_mathematical_invariant():
    with pytest.raises(ValueError, match="Invariante matemática violada"):
        LedgerEntry(
            id="TX-002", product_id="SKU-2", event_type="OUT",
            quantity_change=-5, quantity_before=10, quantity_after=10, # Deveria ser 5
            warehouse_id="WH-1", batch_code="L-2", operator_id="OP-1"
        )
def test_ledger_entry_requires_valid_event_type():
    with pytest.raises(ValueError, match="Tipo de evento inválido"):
        LedgerEntry(
            id="TX-003", product_id="SKU-3", event_type="MAGIC", # Tipo inexistente
            quantity_change=5, quantity_before=5, quantity_after=10,
            warehouse_id="WH-1", batch_code="L-3", operator_id="OP-1"
        )
