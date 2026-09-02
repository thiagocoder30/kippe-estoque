from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text()


def _compact(text: str) -> str:
    return "".join(text.split())


def _putaway_block() -> str:
    javascript = _read("web/js/app.js")

    start = javascript.index(
        "    bindPutawayModule()"
    )

    end = javascript.index(
        "    bindReportsModule()",
        start
    )

    return javascript[start:end]


def test_putaway_exposes_scanner_button():
    html = _read("web/index.html")

    assert 'id="btn-putaway-scanner"' in html
    assert "BIPAR" in html


def test_putaway_scanner_reuses_canonical_scanner_manager():
    javascript = _read("web/js/app.js")

    assert javascript.count(
        "new ScannerManager("
    ) == 1

    assert (
        "new Html5Qrcode("
        not in javascript
    )


def test_putaway_scanner_uses_putaway_target():
    javascript = _compact(
        _read("web/js/app.js")
    )

    assert (
        "this.scannerTarget='putaway'"
        in javascript
    )


def test_scanner_success_routes_to_putaway():
    javascript = _compact(
        _read("web/js/app.js")
    )

    assert (
        "this.scannerTarget==='putaway'"
        in javascript
    )

    assert (
        "document.getElementById('put-ean')"
        in javascript
    )

    assert (
        "decodedText"
        in javascript
    )

    assert (
        "document.getElementById('putaway-modal')"
        in javascript
    )


def test_putaway_scanner_success_loads_product():
    javascript = _compact(
        _read("web/js/app.js")
    )

    assert (
        "loadPutawayProduct(decodedText)"
        in javascript
    )


def test_putaway_has_identified_product_panel():
    html = _read("web/index.html")

    assert 'id="putaway-product-panel"' in html
    assert 'id="putaway-product-name"' in html
    assert 'id="putaway-product-sku"' in html
    assert 'id="putaway-product-ean"' in html


def test_putaway_has_assisted_batch_panel():
    html = _read("web/index.html")

    assert 'id="putaway-batch-panel"' in html
    assert 'id="putaway-batch-expiration"' in html
    assert 'id="putaway-batch-quantity"' in html
    assert 'id="putaway-batch-status"' in html


def test_putaway_product_loader_uses_canonical_query():
    javascript = _putaway_block()

    assert (
        "this.api.queryProduct"
        in javascript
    )


def test_putaway_product_loader_filters_pending_batches():
    javascript = _compact(
        _putaway_block()
    )

    assert (
        "location_id"
        in javascript
    )

    assert (
        "filter("
        in javascript
    )


def test_putaway_product_loader_orders_pending_batches_by_expiration():
    javascript = _compact(
        _putaway_block()
    )

    assert (
        ".sort("
        in javascript
    )

    assert (
        "expiration_date"
        in javascript
    )


def test_putaway_product_loader_prefills_batch():
    javascript = _compact(
        _putaway_block()
    )

    assert (
        "document.getElementById('put-batch')"
        in javascript
    )

    assert (
        ".value="
        in javascript
    )


def test_putaway_close_scanner_restores_putaway_modal():
    javascript = _compact(
        _read("web/js/app.js")
    )

    assert (
        "this.scannerTarget==='putaway'"
        in javascript
    )

    assert (
        "document.getElementById('putaway-modal')"
        in javascript
    )

    assert (
        ".classList.remove('hidden')"
        in javascript
    )


def test_putaway_scanner_failure_restores_modal():
    javascript = _compact(
        _putaway_block()
    )

    assert (
        "this.scanner.status!=='SCANNING'"
        in javascript
    )

    assert (
        "modalPutaway?.classList.remove('hidden')"
        in javascript
    )


def test_putaway_has_inline_error_panel():
    html = _read("web/index.html")

    assert 'id="putaway-error"' in html


def test_putaway_does_not_change_canonical_payload():
    javascript = _compact(
        _putaway_block()
    )

    assert (
        "this.api.registerPutaway({"
        in javascript
    )

    assert (
        "sku:sku"
        in javascript
    )

    assert (
        "batch_code:batchCode"
        in javascript
    )

    assert (
        "location_id:locationId"
        in javascript
    )

    assert (
        "quantity:"
        not in javascript
    )


def test_putaway_does_not_create_second_decoder():
    scanner = _read("web/js/scanner.js")
    app = _read("web/js/app.js")

    assert app.count(
        "new ScannerManager("
    ) == 1

    assert scanner.count(
        "new Html5Qrcode("
    ) == 1
