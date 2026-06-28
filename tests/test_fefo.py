import pytest
from src.domain.product import Product
from datetime import datetime, timedelta

def test_fefo_lotes_complex_resolution():
    p = Product(id="FEFO-03", name="Refrigerante", quantity=0)
    hoje = datetime.today()
    v_curto = (hoje + timedelta(days=5)).strftime("%Y-%m-%d")
    v_longo = (hoje + timedelta(days=20)).strftime("%Y-%m-%d")

    # Recebimento na Doca
    res1 = p.add_stock(10, v_longo, "LOTE-B")
    res2 = p.add_stock(5, v_curto, "LOTE-A")
    assert res1.is_success and res2.is_success
    assert p.quantity == 15

    # Verificando Instruções de Reposição na Gôndola (Pick-List)
    instrucoes = p.get_picking_instructions()
    assert instrucoes[0]['lote'] == "LOTE-A" # Deve ser o primeiro a sair
    assert instrucoes[1]['lote'] == "LOTE-B"

    # Baixa no Caixa
    res_baixa = p.remove_stock(7)
    assert res_baixa.is_success
    assert p.quantity == 8
    
    # O LOTE-A (5 un) deve ter sumido e o LOTE-B deve ter sido abatido em 2 un (10-2=8)
    assert p.batches["LOTE-A"].quantity == 0
    assert p.batches["LOTE-B"]['qty'] == 8
