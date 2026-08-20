from pathlib import Path


def test_index_loads_only_canonical_frontend_entrypoints():

    html = Path("web/index.html").read_text()

    assert "/web/js/app.js" in html
    assert "/web/js/product_search.js" in html

    assert "ui.js" not in html
    assert "router.js" not in html


def test_app_uses_canonical_dependencies():

    javascript = Path("web/js/app.js").read_text()

    assert "import { APIClient } from './api.js';" in javascript
    assert "import { ScannerManager } from './scanner.js';" in javascript

    assert "UIManager" not in javascript
    assert "Router" not in javascript


def test_product_search_uses_canonical_api_client():

    javascript = Path("web/js/product_search.js").read_text()

    assert "import { APIClient } from './api.js';" in javascript

    assert "UIManager" not in javascript
    assert "Router" not in javascript


def test_legacy_frontend_modules_are_not_present():

    assert not Path("web/js/ui.js").exists()
    assert not Path("web/js/router.js").exists()
