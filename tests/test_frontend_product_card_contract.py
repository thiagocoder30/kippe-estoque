from pathlib import Path


def test_product_card_exposes_canonical_operational_fields():

    html = Path("web/index.html").read_text()

    assert 'id="prodEan"' in html
    assert 'id="product-batches"' in html


def test_product_card_batch_template_supports_fefo_fields():

    javascript = Path("web/js/app.js").read_text()

    assert "expiration_status" in javascript
    assert "days_remaining" in javascript
    assert "expiration_date" in javascript
    assert "location_id" in javascript


def test_product_query_renderer_uses_canonical_response_shape():

    javascript = Path("web/js/app.js").read_text()

    assert "data.ean" in javascript
    assert "data.batches" in javascript
    assert "data.quantity" in javascript


def test_frontend_does_not_recalculate_fefo():

    javascript = Path("web/js/app.js").read_text()

    assert "ExpirationAnalyzer" not in javascript
    assert "days_remaining =" not in javascript
