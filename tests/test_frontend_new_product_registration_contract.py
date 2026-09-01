from pathlib import Path


def read_html():
    return Path(
        "web/index.html"
    ).read_text()


def read_app():
    return Path(
        "web/js/app.js"
    ).read_text()


def test_new_product_modal_exposes_only_operational_catalog_fields():
    html = read_html()

    assert 'id="new-product-modal"' in html
    assert 'id="new-product-ean"' in html
    assert 'id="new-product-name"' in html
    assert 'id="new-product-category"' in html
    assert 'id="new-product-unit"' in html
    assert 'id="submit-new-product"' in html

    assert 'id="new-product-sku"' not in html
    assert "SKU INTERNO" not in html


def test_new_product_registration_preserves_unknown_ean():
    javascript = read_app()

    assert "PRODUTO_NAO_CADASTRADO" in javascript
    assert "new-product-ean" in javascript
    assert "openNewProductRegistration" in javascript


def test_new_product_registration_does_not_read_operator_sku():
    javascript = read_app()

    assert "new-product-sku" not in javascript
    assert "id: sku" not in javascript
    assert "id:sku" not in javascript


def test_new_product_registration_uses_canonical_payload_without_id():
    javascript = read_app()

    assert "new-product-name" in javascript
    assert "new-product-category" in javascript
    assert "new-product-unit" in javascript

    assert "ean:" in javascript
    assert "name:" in javascript
    assert "unit_of_measure:" in javascript
    assert "category_id:" in javascript

    assert "this.api.createProduct" in javascript


def test_new_product_registration_requires_ean_and_description_only():
    javascript = read_app()

    assert "Preencha EAN e descrição." in javascript

    assert (
        "Preencha EAN, SKU interno e descrição."
        not in javascript
    )


def test_new_product_success_feedback_has_canonical_fields():
    html = read_html()

    assert 'id="new-product-success-panel"' in html
    assert 'id="new-product-success-name"' in html
    assert 'id="new-product-success-sku"' in html
    assert 'id="new-product-success-ean"' in html

    assert 'id="continue-new-product-receiving"' in html

    assert "PRODUTO CADASTRADO" in html
    assert "CONTINUAR RECEBIMENTO" in html


def test_new_product_registration_consumes_generated_product_response():
    javascript = read_app()

    assert "response.product" in javascript
    assert "new-product-success-sku" in javascript
    assert "new-product-success-name" in javascript
    assert "new-product-success-ean" in javascript


def test_new_product_success_does_not_use_native_alert():
    javascript = read_app()

    assert (
        "✅ PRODUTO CADASTRADO."
        not in javascript
    )


def test_new_product_success_returns_to_receiving_by_explicit_action():
    javascript = read_app()

    assert "continue-new-product-receiving" in javascript
    assert "receive-modal" in javascript
    assert "new-product-modal" in javascript
    assert "loadReceivingProduct" in javascript


def test_new_product_categories_remain_data_driven():
    javascript = read_app()

    assert "this.api.getCategories()" in javascript
    assert "categoryInput.appendChild" in javascript
    assert "document.createElement" in javascript
    assert "'option'" in javascript


def test_new_product_units_remain_canonical():
    html = read_html()

    assert '<option value="un">UN</option>' in html
    assert '<option value="kg">KG</option>' in html
    assert '<option value="lt">LT</option>' in html
