from pathlib import Path


def test_receiving_form_exposes_scanner_control():

    html = Path("web/index.html").read_text()

    assert 'id="rec-ean"' in html
    assert 'id="btn-receive-scanner"' in html


def test_receiving_scanner_uses_dedicated_scanner_manager():

    javascript = Path("web/js/app.js").read_text()

    assert "btn-receive-scanner" in javascript
    assert "this.scanner.start()" in javascript
    assert "this.scanner.open()" not in javascript


def test_receiving_scanner_returns_decoded_ean_to_receiving_field():

    javascript = Path("web/js/app.js").read_text()

    assert "this.scannerTarget === 'receive'" in javascript
    assert "getElementById('rec-ean')" in javascript
    assert "receiveInput.value = decodedText" in javascript


def test_receiving_scanner_reopens_receiving_modal_after_scan():

    javascript = Path("web/js/app.js").read_text()

    assert "getElementById('receive-modal')" in javascript
    assert "receiveModal?.classList.remove('hidden')" in javascript


def test_receiving_scanner_does_not_create_second_html5_qrcode_instance():

    javascript = Path("web/js/app.js").read_text()

    assert "new window.Html5Qrcode" not in javascript
    assert "this.html5QrCode" not in javascript
