from pathlib import Path


def test_api_client_exposes_canonical_product_contracts():

    javascript = Path("web/js/api.js").read_text()

    assert "async queryProduct(identifier)" in javascript
    assert "async suggestProducts(query)" in javascript
    assert "async createProduct(payload)" in javascript


def test_api_client_exposes_canonical_inventory_contracts():

    javascript = Path("web/js/api.js").read_text()

    assert "async registerReceive(payload)" in javascript
    assert "async registerPutaway(payload)" in javascript
    assert "async registerAdjustment(payload)" in javascript


def test_api_client_does_not_expose_legacy_transfer_alias():

    javascript = Path("web/js/api.js").read_text()

    assert "async registerTransfer(payload)" not in javascript


def test_api_client_does_not_expose_legacy_query_aliases():

    javascript = Path("web/js/api.js").read_text()

    assert "async getSku(identifier)" not in javascript
    assert "async searchCatalog(query)" not in javascript


def test_active_frontend_does_not_use_legacy_api_aliases():

    app = Path("web/js/app.js").read_text()
    search = Path("web/js/product_search.js").read_text()

    combined = app + "\n" + search

    assert ".registerTransfer(" not in combined
    assert ".getSku(" not in combined
    assert ".searchCatalog(" not in combined
