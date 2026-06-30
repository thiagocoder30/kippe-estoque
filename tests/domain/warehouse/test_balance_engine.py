import pytest
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.domain.warehouse.balance import BalanceEngine

def test_balance_engine_calculates_total_inventory():
    account = InventoryAccount(sku="DETERGENTE-X")
    
    # +120 Entrada no Chão
    account.record_transaction("L2408", TransactionType.GOODS_RECEIPT, 120, "FLOOR-LIMPEZA", "NF-1")
    # -20 Venda do Chão
    account.record_transaction("L2408", TransactionType.SALE, -20, "FLOOR-LIMPEZA", "PED-1")
    # -10 Transferência do Chão para Estante
    account.record_transaction("L2408", TransactionType.TRANSFER_OUT, -10, "FLOOR-LIMPEZA", "MOV-1")
    # +10 Transferência chegando na Estante
    account.record_transaction("L2408", TransactionType.TRANSFER_IN, 10, "EST-A-01", "MOV-1")
    
    projection = BalanceEngine.calculate(account)
    
    # 120 - 20 - 10 + 10 = 100
    assert projection.total == 100
    
    # O Lote manteve-se o mesmo em todas as operações
    assert len(projection.by_batch) == 1
    assert projection.by_batch["L2408"] == 100
    
    # Projeção Espacial Lean
    assert len(projection.by_location) == 2
    assert projection.by_location["FLOOR-LIMPEZA"] == 90
    assert projection.by_location["EST-A-01"] == 10

def test_balance_engine_cleans_up_zero_balances():
    account = InventoryAccount(sku="CAFE-PILAO-500G")
    
    # Compra 50 unidades para A1
    account.record_transaction("LOTE-X", TransactionType.GOODS_RECEIPT, 50, "EST-C-01", "NF-2")
    # Vende todas as 50
    account.record_transaction("LOTE-X", TransactionType.SALE, -50, "EST-C-01", "PED-2")
    
    projection = BalanceEngine.calculate(account)
    
    assert projection.total == 0
    # Como zerou, os lotes e locais não devem figurar na projeção ativa
    assert "LOTE-X" not in projection.by_batch
    assert "EST-C-01" not in projection.by_location
