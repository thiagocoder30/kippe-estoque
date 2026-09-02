from pathlib import Path


INDEX_PATH = Path("web/index.html")
APP_PATH = Path("web/js/app.js")
SCANNER_PATH = Path("web/js/scanner.js")


def html():
    return INDEX_PATH.read_text()


def app_javascript():
    return APP_PATH.read_text()


def scanner_javascript():
    return SCANNER_PATH.read_text()


def compact(text):
    """
    Normaliza espaços e quebras de linha para que contratos
    semânticos de frontend não dependam da formatação visual
    do JavaScript.
    """
    return "".join(text.split())


def test_new_product_form_exposes_barcode_scanner_button():
    document = html()

    assert 'id="new-product-ean"' in document
    assert 'id="btn-new-product-scanner"' in document
    assert "BIPAR" in document


def test_new_product_ean_remains_readonly_operator_field():
    document = html()

    start = document.index(
        'id="new-product-ean"'
    )

    fragment = document[
        max(0, start - 200):
        start + 500
    ]

    assert "readonly" in fragment


def test_existing_scanner_manager_is_reused_for_new_product():
    javascript = compact(
        app_javascript()
    )

    assert (
        "this.scannerTarget==='new-product'"
        in javascript
    )

    assert (
        "getElementById('new-product-ean')"
        in javascript
    )

    assert (
        "newScannerManager"
        in javascript
    )


def test_new_product_scan_routes_decoded_value_to_ean_field():
    javascript = compact(
        app_javascript()
    )

    target_position = javascript.index(
        "this.scannerTarget==='new-product'"
    )

    fragment = javascript[
        target_position:
        target_position + 1000
    ]

    assert (
        "getElementById('new-product-ean')"
        in fragment
    )

    assert "decodedText" in fragment

    assert (
        "newProductInput.value=decodedText"
        in fragment
    )


def test_new_product_scan_restores_default_scanner_target():
    javascript = compact(
        app_javascript()
    )

    target_position = javascript.index(
        "this.scannerTarget==='new-product'"
    )

    fragment = javascript[
        target_position:
        target_position + 1200
    ]

    assert (
        "this.scannerTarget='search'"
        in fragment
    )


def test_new_product_scanner_button_uses_existing_scanner_instance():
    javascript = compact(
        app_javascript()
    )

    button_position = javascript.index(
        "btn-new-product-scanner"
    )

    fragment = javascript[
        button_position:
        button_position + 1200
    ]

    assert (
        "this.scannerTarget='new-product'"
        in fragment
    )

    assert (
        "this.scanner.start()"
        in fragment
    )

    assert (
        "newHtml5Qrcode"
        not in fragment
    )


def test_scanner_layer_is_above_new_product_modal():
    document = html()

    new_product_position = document.index(
        'id="new-product-modal"'
    )

    new_product_fragment = document[
        new_product_position:
        new_product_position + 300
    ]

    scanner_position = document.index(
        'id="scanner-modal"'
    )

    scanner_fragment = document[
        scanner_position:
        scanner_position + 300
    ]

    assert "z-[180]" in new_product_fragment
    assert "z-[250]" in scanner_fragment


def test_cancelling_new_product_scan_restores_default_target():
    javascript = compact(
        app_javascript()
    )

    close_position = javascript.index(
        "close-scanner-btn"
    )

    fragment = javascript[
        max(0, close_position - 200):
        close_position + 1200
    ]

    assert (
        "this.scannerTarget==='new-product'"
        in fragment
    )

    assert (
        "this.scannerTarget='search'"
        in fragment
    )

    assert (
        "getElementById('new-product-modal')"
        in fragment
    )


def test_operator_has_manual_new_product_entry_point():
    document = html()

    javascript = compact(
        app_javascript()
    )

    assert (
        'id="btn-new-product-registration"'
        in document
    )

    assert (
        "btn-new-product-registration"
        in javascript
    )

    assert (
        "openNewProductRegistration('')"
        in javascript
    )


def test_new_product_scanner_does_not_create_parallel_decoder():
    application = app_javascript()
    scanner = scanner_javascript()

    assert (
        "new Html5Qrcode"
        not in application
    )

    assert application.count(
        "new ScannerManager"
    ) == 1

    assert scanner.count(
        "new Html5Qrcode("
    ) == 1

    assert "BarcodeDetector" not in application
    assert "ZXingBrowser" not in application
    assert "Quagga.decodeSingle" not in application
