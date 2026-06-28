from src.domain.product import Product

def test_add_stock_success():
    p = Product(id="KPC-100", name="Arroz 5kg", quantity=0)
    res = p.add_stock(5, "2030-12-31", "LOTE-X")
    assert res.is_success is True
    assert p.quantity == 5
    assert p.batches["LOTE-X"]['qty'] == 5

def test_add_stock_fail_negative():
    p = Product(id="KPC-100", name="Arroz 5kg", quantity=0)
    res = p.add_stock(-2, "2030-12-31", "LOTE-X")
    assert res.is_success is False
    assert "maior que zero" in res.error

def test_remove_stock_success():
    p = Product(id="KPC-100", name="Arroz 5kg", quantity=0)
    p.add_stock(20, "2030-12-31", "LOTE-X")
    res = p.remove_stock(10)
    assert res.is_success is True
    assert p.quantity == 10

def test_remove_stock_fail_insufficient():
    p = Product(id="KPC-100", name="Arroz 5kg", quantity=0)
    p.add_stock(20, "2030-12-31", "LOTE-X")
    res = p.remove_stock(50)
    assert res.is_success is False
    assert p.quantity == 20
    assert "Política de Estoque Negativo DESATIVADA" in res.error
