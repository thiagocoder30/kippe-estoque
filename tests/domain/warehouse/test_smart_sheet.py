import pytest
from datetime import datetime, timedelta
from src.domain.warehouse.ledger import InventoryAccount, TransactionType
from src.domain.warehouse.smart_sheet import SmartSheetBuilder

def test_smart_sheet_builds_comprehensive_read_model():
    account = InventoryAccount(sku="DETERGENTE-NEUTRO-500ML")
    
    # Recebimento Antigo
    account.record_transaction("L2406", TransactionType.GOODS_RECEIPT, 40, "EST-F-02", "NF-100", 
        {"supplier": "Distribuidora ABC", "expiration_date": (datetime.now() + timedelta(days=25)).strftime("%Y-%m-%d")})
    
    # Venda
    account.record_transaction("L2406", TransactionType.SALE, -8, "EST-F-02", "PED-01")
    
    # Recebimento Novo
    account.record_transaction("L2407", TransactionType.GOODS_RECEIPT, 56, "FLOOR-LIMPEZA", "NF-200",
        {"supplier": "Indústria Ypê", "expiration_date": (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d")})

    # Projeta a Ficha Inteligente (simulando 8 unidades reservadas e 100 de mínimo para forçar alerta)
    sheet = SmartSheetBuilder.build(account, reserved_qty=8, min_stock=100)
    
    # 1. Saldos
    assert sheet.total_balance == (40 - 8 + 56) # 88
    assert sheet.reserved_balance == 8
    assert sheet.available_balance == 80
    
    # 2. Localizações Lean
    assert sheet.locations["EST-F-02"] == 32
    assert sheet.locations["FLOOR-LIMPEZA"] == 56
    
    # 3. Lotes & FEFO
    assert len(sheet.batches) == 2
    assert sheet.next_to_expire is not None
    assert sheet.next_to_expire["id"] == "L2406" # Vence em 25 dias
    
    # 4. Última Entrada
    assert sheet.last_receipt is not None
    assert sheet.last_receipt["supplier"] == "Indústria Ypê"
    assert sheet.last_receipt["nf"] == "NF-200"
    
    # 5. Alertas
    assert any("abaixo do mínimo" in a for a in sheet.alerts)
    assert any("vence em" in a for a in sheet.alerts)
    
    # 6. Histórico
    assert len(sheet.recent_history) == 3
    assert sheet.recent_history[0]["type"] == "GOODS_RECEIPT" # O mais recente primeiro
