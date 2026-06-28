import pytest
from src.domain.batch import Batch
def test_batch_enforces_required_fields():
    with pytest.raises(ValueError, match="código do lote"):
        Batch(code="", product_id="SKU-1", quantity=10, expiration_date="2030-12-31")
    with pytest.raises(ValueError, match="atrelado a um SKU"):
        Batch(code="L01", product_id="", quantity=10, expiration_date="2030-12-31")
def test_batch_denies_negative_quantity():
    with pytest.raises(ValueError, match="não pode ser negativa"):
        Batch(code="L01", product_id="SKU-1", quantity=-5, expiration_date="2030-12-31")
def test_batch_date_format_enforcement():
    with pytest.raises(ValueError, match="Formato de data inválido"):
        Batch(code="L01", product_id="SKU-1", quantity=10, expiration_date="31/12/2030")
def test_batch_backward_compatibility_interface():
    b = Batch(code="L01", product_id="SKU-1", quantity=42, expiration_date="2035-01-01", supplier="NESTLE")
    # Testa se o comportamento polimórfico de dicionário funciona para os testes antigos
    assert b['qty'] == 42
    assert b['exp'] == "2035-01-01"
    assert b['supplier'] == "NESTLE"
