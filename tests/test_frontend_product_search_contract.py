from pathlib import Path


def test_frontend_loads_canonical_product_search_module():

    html = Path("web/index.html").read_text()

    assert "/web/js/product_search.js" in html


def test_product_search_module_uses_canonical_suggestion_client():

    javascript = Path(
        "web/js/product_search.js"
    ).read_text()

    assert "suggestProducts" in javascript
    assert "/api/search" not in javascript


def test_frontend_api_client_uses_canonical_product_contracts():

    javascript = Path(
        "web/js/api.js"
    ).read_text()

    assert "/api/product/query" in javascript
    assert "/api/product/suggestions" in javascript
