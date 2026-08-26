from pathlib import Path


def test_scanner_uses_dynamic_barcode_scan_region():

    javascript = Path("web/js/scanner.js").read_text()

    assert "qrbox: (viewfinderWidth, viewfinderHeight)" in javascript


def test_scanner_scan_region_prioritizes_horizontal_barcodes():

    javascript = Path("web/js/scanner.js").read_text()

    compact = "".join(javascript.split())

    assert "viewfinderWidth*0.9" in compact
    assert "Math.min(160,viewfinderHeight*0.45)" in compact


def test_scanner_does_not_restrict_decoder_to_fixed_format_list():

    javascript = Path("web/js/scanner.js").read_text()

    assert "formatsToSupport" not in javascript


def test_scanner_uses_mobile_friendly_frame_rate():

    javascript = Path("web/js/scanner.js").read_text()

    assert "fps: 15" in javascript
