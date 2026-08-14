from pathlib import Path


def _manual_receiving_block() -> str:
    javascript = Path("web/js/app.js").read_text()

    start = javascript.index(
        "const submitReceive = document.getElementById('submit-receive');"
    )

    end = javascript.index(
        "    bindPutawayModule()",
        start,
    )

    return javascript[start:end]


def test_receiving_form_exposes_canonical_fields():

    html = Path("web/index.html").read_text()

    assert 'id="rec-ean"' in html
    assert 'id="rec-qty"' in html
    assert 'id="rec-batch"' in html
    assert 'id="rec-expiration"' in html
    assert 'id="rec-supplier"' in html


def test_receiving_frontend_uses_canonical_payload_fields():

    javascript = _manual_receiving_block()

    assert "sku:" in javascript
    assert "quantity:" in javascript
    assert "batch_code:" in javascript
    assert "expiration_date:" in javascript
    assert "supplier:" in javascript


def test_receiving_frontend_does_not_fabricate_batch():

    javascript = _manual_receiving_block()

    assert '"LOTE-" + new Date()' not in javascript


def test_receiving_frontend_does_not_fabricate_expiration():

    javascript = _manual_receiving_block()

    assert 'expiration_date: "2027-12-31"' not in javascript


def test_receiving_frontend_uses_canonical_receive_api():

    javascript = _manual_receiving_block()

    assert "this.api.registerReceive" in javascript
