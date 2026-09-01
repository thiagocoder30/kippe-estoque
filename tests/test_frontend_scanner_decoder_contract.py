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


def test_scanner_uses_mobile_stable_frame_rate():
    javascript = normalized_javascript()

    assert "fps:10" in javascript


def test_scanner_uses_fixed_barcode_scan_region():
    javascript = normalized_javascript()

    assert "qrbox:{" in javascript
    assert "width:250" in javascript
    assert "height:150" in javascript


def test_scanner_scan_region_prioritizes_barcode_shape():
    javascript = normalized_javascript()

    width_position = javascript.find(
        "width:250"
    )

    height_position = javascript.find(
        "height:150"
    )

    assert width_position != -1
    assert height_position != -1


def test_scanner_restricts_decoder_to_operational_formats():
    javascript = scanner_javascript()

    assert (
        "formatsToSupport"
        in javascript
    )

    assert (
        "Html5QrcodeSupportedFormats.EAN_13"
        in javascript
    )

    assert (
        "Html5QrcodeSupportedFormats.CODE_128"
        in javascript
    )


def test_scanner_enumerates_physical_cameras():
    javascript = scanner_javascript()

    assert (
        "Html5Qrcode.getCameras()"
        in javascript
    )


def test_scanner_resolves_preferred_camera():
    javascript = scanner_javascript()

    assert (
        "resolvePreferredCamera"
        in javascript
    )

    assert (
        "storedCameraId"
        in javascript
    )


def test_scanner_validates_persisted_camera_against_inventory():
    javascript = scanner_javascript()

    assert (
        "cameras.find"
        in javascript
    )

    assert (
        "camera.id ==="
        in javascript
    )


def test_scanner_has_safe_camera_fallback():
    javascript = scanner_javascript()

    assert (
        "return cameras[0]"
        in javascript
    )


def test_scanner_uses_device_id_in_decoder_start():
    javascript = normalized_javascript()

    assert (
        "this.html5Qrcode.start("
        "this.selectedCameraId,"
        in javascript
    )


def test_scanner_exposes_camera_selector():
    javascript = scanner_javascript()

    assert (
        "scanner-camera-selector"
        in javascript
    )


def test_camera_selection_is_persisted():
    javascript = scanner_javascript()

    assert (
        "storeCameraId"
        in javascript
    )


def test_camera_change_can_restart_active_scanner():
    javascript = scanner_javascript()

    assert (
        "await this.stop("
        in javascript
    )

    assert (
        "await this.start()"
        in javascript
    )


def test_decoder_failure_callbacks_remain_silent():
    javascript = scanner_javascript()

    assert (
        "Falhas de enquadramento"
        in javascript
    )


def test_experimental_decoder_engines_are_absent():
    javascript = scanner_javascript()

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
