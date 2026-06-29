import pytest
from src.domain.procurement.order import PurchaseOrder, MonetaryValue
from src.domain.procurement.invoice import SupplierInvoice, SupplierInvoiceLine
from src.domain.procurement.three_way_match import ThreeWayMatchEngine

def setup_base_order_and_receipt():
    order = PurchaseOrder(id="PO-3W-001", supplier_id="SUP-CORP")
    order.add_item(sku="SKU-A", quantity=100, unit_price=10.0)
    order.add_item(sku="SKU-B", quantity=50, unit_price=20.0)
    order.submit()
    order.start_approval()
    order.approve()
    order.place_order()
    
    # Simulação de Recebimento Físico Perfeito
    order.receive_item("SKU-A", 100)
    order.receive_item("SKU-B", 50)
    return order

def test_three_way_match_perfect_scenario():
    order = setup_base_order_and_receipt()
    
    invoice = SupplierInvoice(invoice_number="NFE-001", supplier_id="SUP-CORP")
    invoice.lines.append(SupplierInvoiceLine(sku="SKU-A", quantity=100, unit_price=MonetaryValue(10.0)))
    invoice.lines.append(SupplierInvoiceLine(sku="SKU-B", quantity=50, unit_price=MonetaryValue(20.0)))
    
    result = ThreeWayMatchEngine.evaluate(order, invoice)
    
    assert result.is_matched is True
    assert len(result.divergences) == 0
    assert not result.quantity_delta
    assert not result.price_delta

def test_three_way_match_fails_on_quantity_divergence():
    order = setup_base_order_and_receipt()
    
    invoice = SupplierInvoice(invoice_number="NFE-002", supplier_id="SUP-CORP")
    # Fornecedor cobrando 110 itens, mas recebemos fisicamente 100
    invoice.lines.append(SupplierInvoiceLine(sku="SKU-A", quantity=110, unit_price=MonetaryValue(10.0)))
    
    result = ThreeWayMatchEngine.evaluate(order, invoice)
    
    assert result.is_matched is False
    assert "Divergência de quantidade no SKU SKU-A" in result.divergences[0]
    assert result.quantity_delta["SKU-A"] == 10  # Delta positivo de 10 na fatura

def test_three_way_match_fails_on_price_divergence():
    order = setup_base_order_and_receipt()
    
    invoice = SupplierInvoice(invoice_number="NFE-003", supplier_id="SUP-CORP")
    # Fornecedor cobrando preço maior que o aprovado no pedido
    invoice.lines.append(SupplierInvoiceLine(sku="SKU-A", quantity=100, unit_price=MonetaryValue(12.5)))
    
    result = ThreeWayMatchEngine.evaluate(order, invoice)
    
    assert result.is_matched is False
    assert "Divergência de preço no SKU SKU-A" in result.divergences[0]
    assert result.price_delta["SKU-A"] == 2.5  # Delta financeiro positivo

def test_three_way_match_fails_on_unauthorized_sku():
    order = setup_base_order_and_receipt()
    
    invoice = SupplierInvoice(invoice_number="NFE-004", supplier_id="SUP-CORP")
    invoice.lines.append(SupplierInvoiceLine(sku="SKU-FANTASMA", quantity=10, unit_price=MonetaryValue(5.0)))
    
    result = ThreeWayMatchEngine.evaluate(order, invoice)
    
    assert result.is_matched is False
    assert "não consta no pedido de compra" in result.divergences[0]

def test_three_way_match_fails_on_supplier_mismatch():
    order = setup_base_order_and_receipt()
    
    # Fatura emitida por fornecedor diferente do PO aprovado
    invoice = SupplierInvoice(invoice_number="NFE-005", supplier_id="SUP-FRAUDE")
    result = ThreeWayMatchEngine.evaluate(order, invoice)
    
    assert result.is_matched is False
    assert "difere do fornecedor do pedido" in result.divergences[0]
