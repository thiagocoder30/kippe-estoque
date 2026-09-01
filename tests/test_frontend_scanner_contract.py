from pathlib import Path


SCANNER_PATH = Path(
    "web/js/scanner.js"
)


def scanner_javascript():
    return SCANNER_PATH.read_text(
        encoding="utf-8"
    )


def normalized_javascript():
    return "".join(
        scanner_javascript().split()
    )


def test_scanner_manager_owns_html5_qrcode_instance():
    javascript = scanner_javascript()

    assert "this.html5Qrcode" in javascript
    assert "new Html5Qrcode" in javascript


def test_scanner_manager_uses_single_decoder_engine():
    javascript = scanner_javascript()

    assert "Html5Qrcode" in javascript

    assert (
        "new window.BarcodeDetector"
        not in javascript
    )

    assert (
        "ZXingBrowser"
        not in javascript
    )

    assert (
        "Quagga.decodeSingle"
        not in javascript
    )


def test_scanner_supports_ean13_and_code128():
    javascript = scanner_javascript()

    assert (
        "Html5QrcodeSupportedFormats.EAN_13"
        in javascript
    )

    assert (
        "Html5QrcodeSupportedFormats.CODE_128"
        in javascript
    )


def test_scanner_uses_explicit_format_contract():
    javascript = scanner_javascript()

    assert "formatsToSupport" in javascript


def test_scanner_owns_modal_contract():
    javascript = scanner_javascript()

    assert (
        "scanner-modal"
        in javascript
    )

    assert (
        "close-scanner-btn"
        in javascript
    )

    assert (
        "reader"
        in javascript
    )


def test_scanner_has_lifecycle_states():
    javascript = scanner_javascript()

    for state in (
        "IDLE",
        "STARTING",
        "SCANNING",
        "STOPPING",
    ):
        assert state in javascript


def test_scanner_recreates_decoder_between_sessions():
    javascript = scanner_javascript()

    assert (
        "destroyScannerInstance"
        in javascript
    )

    assert (
        "this.html5Qrcode ="
        in javascript
    )

    assert (
        "this.html5Qrcode =\n"
        in javascript
        or
        "this.html5Qrcode =" in javascript
    )


def test_scanner_stops_and_clears_decoder():
    javascript = scanner_javascript()

    assert (
        "await scanner.stop()"
        in javascript
    )

    assert (
        "await scanner.clear()"
        in javascript
    )


def test_scanner_vibrates_on_success():
    javascript = scanner_javascript()

    assert (
        "navigator.vibrate"
        in javascript
    )


def test_scanner_routes_success_to_callback():
    javascript = scanner_javascript()

    assert (
        "this.onScanSuccess"
        in javascript
    )

    assert (
        "callback("
        in javascript
    )


def test_scanner_uses_explicit_selected_camera_id():
    javascript = normalized_javascript()

    assert (
        "this.html5Qrcode.start("
        "this.selectedCameraId,"
        in javascript
    )


def test_scanner_persists_camera_preference():
    javascript = scanner_javascript()

    assert (
        "kippe.scanner.preferredCameraId"
        in javascript
    )

    assert (
        "window.localStorage.getItem"
        in javascript
    )

    assert (
        "window.localStorage.setItem"
        in javascript
    )
