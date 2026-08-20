from pathlib import Path


def test_new_product_registration_modal_exposes_canonical_fields():

    html = Path("web/index.html").read_text()

    assert 'id="new-product-modal"' in html
    assert 'id="new-product-ean"' in html
    assert 'id="new-product-sku"' in html
    assert 'id="new-product-name"' in html
    assert 'id="new-product-category"' in html
    assert 'id="new-product-unit"' in html
    assert 'id="submit-new-product"' in html


def test_new_product_registration_preserves_unknown_ean():

    javascript = Path("web/js/app.js").read_text()

    assert "PRODUTO_NAO_CADASTRADO" in javascript
    assert "new-product-ean" in javascript


def test_new_product_registration_uses_operator_supplied_sku():

    javascript = Path("web/js/app.js").read_text()

    assert "new-product-sku" in javascript

    assert "sku = ean" not in javascript
    assert "sku: ean" not in javascript


def test_new_product_registration_uses_canonical_product_payload():

    javascript = Path("web/js/app.js").read_text()

    assert "new-product-name" in javascript
    assert "new-product-category" in javascript
    assert "new-product-unit" in javascript

    assert "ean:" in javascript
    assert "unit_of_measure:" in javascript
    assert "category_id:" in javascript


def test_new_product_registration_returns_to_receiving_flow():

    javascript = Path("web/js/app.js").read_text()

    assert "receive-modal" in javascript
    assert "new-product-modal" in javascript
