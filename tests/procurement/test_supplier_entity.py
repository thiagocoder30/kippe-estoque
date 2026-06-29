import pytest
from src.domain.procurement.supplier import Supplier

def test_supplier_canonical_creation_success():
    supplier = Supplier(
        id="SUP-001",
        corporate_name="Tech Distribuidora S.A.",
        tax_id="63.269.720/0001-77",
        email="contato@techdistribuidora.com.br",
        lead_time_days=5
    )
    assert supplier.id == "SUP-001"
    assert supplier.status == "ACTIVE"
    assert supplier.lead_time_days == 5

def test_supplier_enforces_required_fields():
    with pytest.raises(ValueError, match="ID do fornecedor é obrigatório"):
        Supplier(id="", corporate_name="Fornecedor X", tax_id="123", email="x@x.com")
        
    with pytest.raises(ValueError, match="Razão Social \\(corporate_name\\) é obrigatória"):
        Supplier(id="SUP-002", corporate_name="", tax_id="123", email="x@x.com")
        
    with pytest.raises(ValueError, match="Documento Fiscal \\(tax_id\\) é obrigatório"):
        Supplier(id="SUP-003", corporate_name="Fornecedor Y", tax_id="", email="y@y.com")

def test_supplier_enforces_valid_email():
    with pytest.raises(ValueError, match="endereço de email fornecido é inválido"):
        Supplier(id="SUP-004", corporate_name="Fornecedor W", tax_id="123", email="email-invalido.com")

def test_supplier_enforces_positive_lead_time():
    with pytest.raises(ValueError, match="lead time logístico não pode ser negativo"):
        Supplier(id="SUP-005", corporate_name="Fornecedor Z", tax_id="123", email="z@z.com", lead_time_days=-2)

def test_supplier_enforces_valid_status():
    with pytest.raises(ValueError, match="Status do fornecedor inválido"):
        Supplier(id="SUP-006", corporate_name="Fornecedor H", tax_id="123", email="h@h.com", status="BANNED")
