from pathlib import Path


def _putaway_block() -> str:
    javascript = Path("web/js/app.js").read_text()

    start = javascript.index(
        "    bindPutawayModule()"
    )

    end = javascript.index(
        "    bindReportsModule()",
        start,
    )

    return javascript[start:end]


def test_putaway_form_exposes_canonical_fields():

    html = Path("web/index.html").read_text()

    assert 'id="put-ean"' in html
    assert 'id="put-batch"' in html
    assert 'id="put-location"' in html
    assert 'id="submit-putaway"' in html


def test_putaway_form_does_not_request_quantity():

    html = Path("web/index.html").read_text()

    assert 'id="put-qty"' not in html


def test_putaway_frontend_uses_canonical_api():

    javascript = _putaway_block()

    assert "this.api.registerPutaway" in javascript
    assert "this.api.registerTransfer" not in javascript


def test_putaway_frontend_sends_batch_and_location():

    javascript = _putaway_block()

    assert "batch_code:" in javascript
    assert "location_id:" in javascript


def test_putaway_frontend_does_not_send_transfer_quantity():

    javascript = _putaway_block()

    assert "amount:" not in javascript
    assert "quantity:" not in javascript
