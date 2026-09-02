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
        start,
    )

    return javascript[start:end]


def test_putaway_has_kippe_success_panel():
    html = _read("web/index.html")

    assert 'id="putaway-success-modal"' in html
    assert 'id="putaway-success-product"' in html
    assert 'id="putaway-success-batch"' in html
    assert 'id="putaway-success-location"' in html


def test_putaway_success_panel_has_continue_action():
    html = _read("web/index.html")

    assert 'id="btn-putaway-success-continue"' in html

    assert (
        "CONTINUAR"
        in html
    )


def test_putaway_does_not_use_native_success_alert():
    javascript = _putaway_block()

    assert (
        "alert("
        not in javascript
    )


def test_putaway_success_populates_operational_data():
    javascript = _compact(
        _putaway_block()
    )

    assert (
        "document.getElementById('putaway-success-product')"
        in javascript
    )

    assert (
        "document.getElementById('putaway-success-batch')"
        in javascript
    )

    assert (
        "document.getElementById('putaway-success-location')"
        in javascript
    )


def test_putaway_success_shows_kippe_modal():
    javascript = _compact(
        _putaway_block()
    )

    assert (
        "document.getElementById('putaway-success-modal')"
        in javascript
    )

    assert (
        ".classList.remove('hidden')"
        in javascript
    )


def test_putaway_success_closes_operational_modal():
    javascript = _compact(
        _putaway_block()
    )

    assert (
        "modalPutaway?.classList.add('hidden')"
        in javascript
    )


def test_putaway_continue_closes_success_panel():
    javascript = _compact(
        _putaway_block()
    )

    assert (
        "btn-putaway-success-continue"
        in javascript
    )

    assert (
        "putaway-success-modal"
        in javascript
    )


def test_putaway_success_keeps_canonical_backend_command():
    javascript = _compact(
        _putaway_block()
    )

    assert (
        "this.api.registerPutaway({"
        "sku:sku,"
        "batch_code:batchCode,"
        "location_id:locationId,"
        "})"
        in javascript
    )

    assert "quantity:" not in javascript


def test_putaway_success_does_not_create_new_scanner():
    javascript = _read("web/js/app.js")

    assert (
        javascript.count(
            "new ScannerManager("
        )
        == 1
    )

    assert (
        "new Html5Qrcode("
        not in javascript
    )
