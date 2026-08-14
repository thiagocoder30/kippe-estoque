from pathlib import Path


def test_app_uses_dedicated_scanner_manager():

    javascript = Path("web/js/app.js").read_text()

    assert "import { ScannerManager } from './scanner.js';" in javascript
    assert "new ScannerManager" in javascript


def test_app_does_not_own_html5_qrcode_instance():

    javascript = Path("web/js/app.js").read_text()

    assert "this.html5QrCode" not in javascript
    assert "new window.Html5Qrcode" not in javascript


def test_scanner_result_uses_canonical_product_query_flow():

    javascript = Path("web/js/app.js").read_text()

    assert "fetchAndRenderSku(decodedText)" in javascript


def test_scanner_manager_supports_operational_barcode_formats():

    javascript = Path("web/js/scanner.js").read_text()

    assert "Html5QrcodeSupportedFormats.EAN_13" in javascript
    assert "Html5QrcodeSupportedFormats.CODE_128" in javascript
