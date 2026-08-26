from pathlib import Path


def test_app_uses_dedicated_scanner_manager():

    javascript = Path("web/js/app.js").read_text()

    assert "import { ScannerManager } from './scanner.js';" in javascript
    assert "new ScannerManager" in javascript


def test_app_does_not_own_html5_qrcode_instance():

    javascript = Path("web/js/app.js").read_text()

    assert "this.html5QrCode" not in javascript
    assert "new Html5Qrcode" not in javascript
    assert "new window.Html5Qrcode" not in javascript


def test_scanner_manager_owns_html5_qrcode_instance():

    javascript = Path("web/js/scanner.js").read_text()

    assert "this.html5Qrcode" in javascript
    assert 'new Html5Qrcode("reader")' in javascript


def test_scanner_manager_supports_operational_barcode_detection():

    javascript = Path("web/js/scanner.js").read_text()

    assert "formatsToSupport" not in javascript
    assert "qrbox: (viewfinderWidth, viewfinderHeight)" in javascript
    assert "fps: 15" in javascript
