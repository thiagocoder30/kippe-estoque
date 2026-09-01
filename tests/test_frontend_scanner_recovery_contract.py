from pathlib import Path


SCANNER_PATH = Path(
    "web/js/scanner.js"
)

INDEX_PATH = Path(
    "web/index.html"
)

APP_PATH = Path(
    "web/js/app.js"
)


def scanner_javascript():
    return SCANNER_PATH.read_text(
        encoding="utf-8"
    )


def normalized_scanner():
    return "".join(
        scanner_javascript().split()
    )


def index_html():
    return INDEX_PATH.read_text(
        encoding="utf-8"
    )


def app_javascript():
    return APP_PATH.read_text(
        encoding="utf-8"
    )


def test_scanner_uses_only_html5_qrcode_runtime():
    javascript = scanner_javascript()

    assert (
        "new Html5Qrcode"
        in javascript
    )

    assert (
        "new window.BarcodeDetector"
        not in javascript
    )

    assert (
        "'BarcodeDetector' in window"
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


def test_scanner_supports_ean13():
    javascript = scanner_javascript()

    assert (
        "Html5QrcodeSupportedFormats.EAN_13"
        in javascript
    )


def test_scanner_supports_code128():
    javascript = scanner_javascript()

    assert (
        "Html5QrcodeSupportedFormats.CODE_128"
        in javascript
    )


def test_scanner_preserves_optical_configuration():
    javascript = normalized_scanner()

    assert "fps:10" in javascript
    assert "width:250" in javascript
    assert "height:150" in javascript


def test_scanner_enumerates_cameras_through_html5_qrcode():
    javascript = scanner_javascript()

    assert (
        "Html5Qrcode.getCameras()"
        in javascript
    )


def test_scanner_uses_explicit_camera_id():
    javascript = normalized_scanner()

    assert (
        "this.html5Qrcode.start("
        "this.selectedCameraId,"
        in javascript
    )


def test_scanner_has_preferred_camera_storage_key():
    javascript = scanner_javascript()

    assert (
        "kippe.scanner.preferredCameraId"
        in javascript
    )


def test_scanner_reads_preferred_camera_from_local_storage():
    javascript = scanner_javascript()

    assert (
        "window.localStorage.getItem"
        in javascript
    )


def test_scanner_persists_selected_camera():
    javascript = scanner_javascript()

    assert (
        "window.localStorage.setItem"
        in javascript
    )


def test_scanner_validates_stored_camera_against_inventory():
    javascript = scanner_javascript()

    assert (
        "camera.id ==="
        in javascript
    )

    assert (
        "storedCameraId"
        in javascript
    )


def test_scanner_has_safe_fallback_camera():
    javascript = scanner_javascript()

    assert (
        "return cameras[0]"
        in javascript
    )


def test_scanner_exposes_camera_selector():
    javascript = scanner_javascript()

    assert (
        "scanner-camera-selector"
        in javascript
    )


def test_camera_change_is_persisted():
    javascript = scanner_javascript()

    assert (
        "this.storeCameraId("
        in javascript
    )


def test_camera_change_restarts_active_scanner():
    javascript = scanner_javascript()

    assert (
        "await this.stop("
        in javascript
    )

    assert (
        "await this.start()"
        in javascript
    )


def test_decoder_instance_is_recreated():
    javascript = scanner_javascript()

    assert (
        "await this.destroyScannerInstance()"
        in javascript
    )

    assert (
        "new Html5Qrcode("
        in javascript
    )


def test_success_vibrates():
    javascript = scanner_javascript()

    assert (
        "navigator.vibrate"
        in javascript
    )


def test_success_routes_to_existing_callback():
    javascript = scanner_javascript()

    assert (
        "this.onScanSuccess"
        in javascript
    )

    assert (
        "callback("
        in javascript
    )


def test_scanner_modal_contract_is_preserved():
    html = index_html()

    assert (
        'id="scanner-modal"'
        in html
    )

    assert (
        'id="close-scanner-btn"'
        in html
    )

    assert (
        'id="reader"'
        in html
    )


def test_html5_qrcode_is_version_pinned():
    html = index_html()

    assert (
        "html5-qrcode@2.3.8"
        in html
    )


def test_zxing_bundle_is_absent():
    html = index_html()

    assert (
        "@zxing/browser"
        not in html
    )


def test_quagga_bundle_is_absent():
    html = index_html()

    assert (
        "@ericblade/quagga2"
        not in html
    )


def test_app_keeps_scanner_manager():
    javascript = app_javascript()

    assert (
        "new ScannerManager"
        in javascript
    )


def test_app_keeps_scanner_start_contract():
    javascript = app_javascript()

    assert (
        "this.scanner.start()"
        in javascript
    )


def test_receiving_scanner_target_is_preserved():
    javascript = app_javascript()

    assert (
        "this.scannerTarget = 'receive'"
        in javascript
    )

    assert (
        "this.loadReceivingProduct"
        in javascript
    )
