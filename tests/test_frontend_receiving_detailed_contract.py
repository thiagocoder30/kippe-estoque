from pathlib import Path


def test_receiving_modal_exposes_detailed_operational_sections():

    html = Path("web/index.html").read_text()

    assert 'id="receive-modal"' in html

    assert 'id="receive-product-section"' in html
    assert 'id="receive-document-section"' in html
    assert 'id="receive-traceability-section"' in html
    assert 'id="receive-quantity-section"' in html
    assert 'id="receive-logistics-section"' in html
    assert 'id="receive-summary-section"' in html


def test_receiving_form_exposes_document_and_traceability_fields():

    html = Path("web/index.html").read_text()

    assert 'id="rec-supplier"' in html
    assert 'id="rec-invoice"' in html
    assert 'id="rec-origin"' in html

    assert 'id="rec-batch"' in html
    assert 'id="rec-manufacturing"' in html
    assert 'id="rec-expiration"' in html


def test_receiving_form_exposes_product_identification_card():

    html = Path("web/index.html").read_text()

    assert 'id="receive-product-card"' in html
    assert 'id="receive-product-name"' in html
    assert 'id="receive-product-sku"' in html
    assert 'id="receive-product-ean"' in html
    assert 'id="receive-product-unit"' in html


def test_receiving_form_exposes_expiration_intelligence():

    html = Path("web/index.html").read_text()

    assert 'id="receive-expiration-status"' in html
    assert 'id="receive-expiration-days"' in html


def test_receiving_form_exposes_quantity_controls():

    html = Path("web/index.html").read_text()

    assert 'id="rec-qty"' in html
    assert 'id="rec-qty-minus"' in html
    assert 'id="rec-qty-plus"' in html


def test_receiving_form_exposes_pending_putaway_status():

    html = Path("web/index.html").read_text()

    assert 'id="receive-putaway-status"' in html
    assert "AGUARDANDO ARMAZENAGEM" in html


def test_receiving_form_exposes_operational_summary():

    html = Path("web/index.html").read_text()

    assert 'id="receive-summary-product"' in html
    assert 'id="receive-summary-batch"' in html
    assert 'id="receive-summary-expiration"' in html
    assert 'id="receive-summary-supplier"' in html
    assert 'id="receive-summary-invoice"' in html
    assert 'id="receive-summary-quantity"' in html


def test_receiving_frontend_sends_detailed_payload():

    javascript = Path("web/js/app.js").read_text()

    assert "manufacturing_date:" in javascript
    assert "invoice_id:" in javascript
    assert "origin_document:" in javascript


def test_receiving_frontend_uses_operational_response():

    javascript = Path("web/js/app.js").read_text()

    assert "receiving.putaway_status" in javascript
    assert "receiving.batch_code" in javascript
    assert "receiving.quantity" in javascript
