from pathlib import Path


def test_receiving_quantity_section_exposes_entry_mode_controls():

    html = Path("web/index.html").read_text()

    assert 'id="rec-entry-mode-unit"' in html
    assert 'id="rec-entry-mode-package"' in html

    assert "UNIDADES" in html
    assert "FARDO / CAIXA" in html


def test_receiving_package_mode_exposes_package_fields():

    html = Path("web/index.html").read_text()

    assert 'id="rec-package-fields"' in html
    assert 'id="rec-units-per-package"' in html
    assert 'id="rec-package-qty"' in html


def test_receiving_exposes_readonly_total_units():

    html = Path("web/index.html").read_text()

    assert 'id="rec-total-units"' in html

    block = html.split(
        'id="rec-total-units"',
        1,
    )[1][:500]

    assert "readonly" in block


def test_receiving_frontend_tracks_unit_and_package_modes():

    javascript = Path("web/js/app.js").read_text()

    assert "UNIT" in javascript
    assert "PACKAGE" in javascript
    assert "rec-entry-mode-unit" in javascript
    assert "rec-entry-mode-package" in javascript


def test_receiving_frontend_calculates_package_total_in_units():

    javascript = Path("web/js/app.js").read_text()
    compact = "".join(javascript.split())

    assert "rec-units-per-package" in javascript
    assert "rec-package-qty" in javascript

    assert (
        "unitsPerPackage*packageQuantity"
        in compact
    )


def test_receiving_frontend_keeps_quantity_payload_canonical_in_units():

    javascript = Path("web/js/app.js").read_text()

    assert "quantity: quantity" in javascript

    assert "package_quantity:" not in javascript
    assert "units_per_package:" not in javascript


def test_receiving_summary_exposes_package_calculation():

    html = Path("web/index.html").read_text()

    assert 'id="receive-summary-packaging"' in html


def test_receiving_submit_label_uses_total_units():

    javascript = Path("web/js/app.js").read_text()

    assert "CONFIRMAR RECEBIMENTO" in javascript
    assert "rec-total-units" in javascript
