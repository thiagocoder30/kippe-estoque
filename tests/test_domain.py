from src.domain.product import Product

def test_add_stock_success():
    p = Product(id="KPC-100", name="Arroz 5kg", quantity=20)
    res = p.add_stock(5)
    assert res.is_success is True
    assert p.quantity == 25

def test_add_stock_fail_negative():
    p = Product(id="KPC-100", name="Arroz 5kg", quantity=20)
    res = p.add_stock(-2)
    assert res.is_success is False
    assert res.error == "Violação de Regra: A quantidade de entrada deve ser > 0."

def test_remove_stock_success():
    p = Product(id="KPC-100", name="Arroz 5kg", quantity=20)
    res = p.remove_stock(10)
    assert res.is_success is True
    assert p.quantity == 10

def test_remove_stock_fail_insufficient():
    p = Product(id="KPC-100", name="Arroz 5kg", quantity=20)
    res = p.remove_stock(50)
    assert res.is_success is False
    assert p.quantity == 20
    assert res.error == "Violação de Regra: Estoque insuficiente para a transação."
