from src.domain.product import Product
from src.use_cases.manage_stock import ManageStockUseCase

def test_manage_stock_use_case_add():
    uc = ManageStockUseCase()
    p = Product(id="KPC-200", name="Feijão 1kg", quantity=10)
    
    res = uc.execute_add(p, 5)
    assert res.is_success is True
    assert p.quantity == 15

def test_manage_stock_use_case_remove():
    uc = ManageStockUseCase()
    p = Product(id="KPC-200", name="Feijão 1kg", quantity=10)
    
    res = uc.execute_remove(p, 3)
    assert res.is_success is True
    assert p.quantity == 7

def test_manage_stock_use_case_remove_fail():
    uc = ManageStockUseCase()
    p = Product(id="KPC-200", name="Feijão 1kg", quantity=10)
    
    res = uc.execute_remove(p, 15)
    assert res.is_success is False
    assert res.error == "Violação de Regra: Estoque insuficiente para a transação."
