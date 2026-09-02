from pathlib import Path


APP_PATH = Path("web/js/app.js")


def compact(text):
    return "".join(text.split())


def app_javascript():
    return compact(
        APP_PATH.read_text()
    )


def new_product_scanner_fragment():
    javascript = app_javascript()

    start = javascript.index(
        "btn-new-product-scanner"
    )

    end = javascript.index(
        "submit-new-product",
        start
    )

    return javascript[
        start:end
    ]


def test_new_product_scanner_checks_runtime_state_after_start():
    fragment = new_product_scanner_fragment()

    assert (
        "awaitthis.scanner.start();"
        in fragment
    )

    assert (
        "this.scanner.status!=='SCANNING'"
        in fragment
    )


def test_failed_new_product_scanner_start_restores_registration_modal():
    fragment = new_product_scanner_fragment()

    assert (
        "this.scanner.status!=='SCANNING'"
        in fragment
    )

    assert (
        "newProductModal?.classList.remove('hidden')"
        in fragment
    )

    assert (
        "this.scannerTarget='search'"
        in fragment
    )


def test_failed_new_product_scanner_start_exposes_inline_error():
    fragment = new_product_scanner_fragment()

    assert (
        "getElementById('new-product-error')"
        in fragment
    )

    assert (
        "Nãofoipossívelabriroscanner."
        in fragment
    )

    assert (
        "errorPanel.classList.remove('hidden')"
        in fragment
    )


def test_new_product_scanner_failure_does_not_create_another_decoder():
    javascript = app_javascript()

    assert (
        "newHtml5Qrcode"
        not in javascript
    )

    assert javascript.count(
        "newScannerManager"
    ) == 1
