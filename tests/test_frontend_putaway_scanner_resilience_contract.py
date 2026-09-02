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


def test_putaway_batch_is_readonly():
    html = _read("web/index.html")

    fragment = html.split(
        'id="put-batch"',
        1,
    )[1][:500]

    assert "readonly" in fragment


def test_putaway_does_not_guess_physical_location():
    javascript = _putaway_block()

    forbidden = [
        "BOX-A1",
        "BOX-A2",
        "BOX-B1",
        "BOX-B2",
        "CHAO-LIMPEZA",
        "EXT-ZAB",
    ]

    for value in forbidden:
        assert value not in javascript


def test_putaway_location_remains_operator_selected():
    javascript = _compact(
        _putaway_block()
    )

    assert (
        "document.getElementById('put-location')"
        in javascript
    )

    assert (
        "location_id:locationId"
        in javascript
    )


def test_putaway_only_considers_unaddressed_batches():
    javascript = _compact(
        _putaway_block()
    )

    assert (
        ".filter((batch)=>!batch.location_id)"
        in javascript
    )


def test_putaway_prioritizes_expiration_date():
    javascript = _compact(
        _putaway_block()
    )

    assert "expiration_date" in javascript
    assert "localeCompare(" in javascript


def test_putaway_no_pending_batch_is_not_fabricated():
    javascript = _putaway_block()

    assert (
        "Este produto não possui lote "
        in javascript
    )

    assert (
        "pendente de armazenagem."
        in javascript
    )

    forbidden = [
        "L001",
        "LOTE-001",
        "B001",
        "new Date()",
    ]

    for value in forbidden:
        assert value not in javascript


def test_putaway_query_error_does_not_fabricate_product():
    javascript = _putaway_block()

    assert (
        "Produto não encontrado."
        in javascript
    )

    forbidden = [
        "PRODUTO PADRAO",
        "PRODUTO GENÉRICO",
        "SKU000001",
    ]

    for value in forbidden:
        assert value not in javascript


def test_putaway_scan_success_normalizes_to_canonical_sku():
    javascript = _compact(
        _putaway_block()
    )

    assert (
        "putEan.value=data.id||data.sku||normalized"
        in javascript
    )


def test_putaway_scanner_failure_resets_target():
    javascript = _compact(
        _putaway_block()
    )

    assert (
        "this.scanner.status!=='SCANNING'"
        in javascript
    )

    assert (
        "this.scannerTarget='search'"
        in javascript
    )

    assert (
        "Nãofoipossívelabriroscanner."
        in javascript
    )


def test_putaway_scanner_cancel_restores_modal_and_target():
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
        "this.scannerTarget='search'"
        in javascript
    )


def test_putaway_does_not_modify_scanner_engine_contract():
    scanner = _read("web/js/scanner.js")
    app = _read("web/js/app.js")

    assert (
        app.count(
            "new ScannerManager("
        )
        == 1
    )

    assert (
        scanner.count(
            "new Html5Qrcode("
        )
        == 1
    )

    assert "BarcodeDetector" not in app
    assert "ZXing" not in app
    assert "Quagga" not in app


def test_putaway_keeps_canonical_backend_payload():
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
    assert "warehouse_id:" not in javascript


def test_putaway_product_panel_uses_canonical_batch_status():
    javascript = _putaway_block()

    assert "expiration_status" in javascript
    assert "expiration_date" in javascript
    assert "quantity" in javascript


def test_putaway_does_not_recalculate_expiration_locally():
    javascript = _putaway_block()

    assert "ExpirationAnalyzer" not in javascript
    assert "days_remaining =" not in javascript
    assert "86400000" not in javascript
