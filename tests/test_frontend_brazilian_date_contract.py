from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "web/js/app.js"


def read_app() -> str:
    return APP_PATH.read_text()


def compact(text: str) -> str:
    return "".join(text.split())


def method_block(
    source: str,
    start_marker: str,
    end_marker: str,
) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


def test_frontend_exposes_canonical_brazilian_date_formatter():
    source = read_app()

    assert "formatDateBR(" in source


def test_date_formatter_does_not_use_javascript_date_parsing():
    source = read_app()

    start = source.index("    formatDateBR(")

    end = source.index(
        "    updateReceivingExpirationIntelligence()",
        start,
    )

    block = source[start:end]

    assert "new Date(" not in block
    assert "toLocaleDateString" not in block


def test_date_formatter_recognizes_iso_calendar_date():
    source = compact(read_app())

    assert (
        "/^\\d{4}-\\d{2}-\\d{2}$/"
        in source
        or
        "^\\d{4}-\\d{2}-\\d{2}$"
        in source
    )


def test_receiving_summary_formats_expiration_for_display():
    source = method_block(
        read_app(),
        "    updateReceivingSummary()",
        "    resetReceivingForm()",
    )

    compacted = compact(source)

    assert (
        "this.formatDateBR(expiration"
        in compacted
    )


def test_putaway_formats_expiration_for_display():
    source = read_app()

    start = source.index(
        "const batchExpiration ="
    )

    end = source.index(
        "if (batchQuantity)",
        start,
    )

    block = compact(source[start:end])

    assert (
        "this.formatDateBR("
        in block
    )

    assert "selectedBatch.expiration_date" in block


def test_expiration_report_formats_date_for_display():
    source = read_app()

    assert (
        "this.formatDateBR(item.expiration"
        in compact(source)
    )


def test_product_batch_card_formats_expiration_for_display():
    source = read_app()

    assert (
        "this.formatDateBR(batch.expiration_date"
        in compact(source)
    )


def test_fefo_sort_keeps_raw_iso_expiration_date():
    source = read_app()

    start = source.index(
        "const pendingBatches ="
    )

    end = source.index(
        "if (",
        start,
    )

    block = source[start:end]

    assert "left.expiration_date" in block
    assert "right.expiration_date" in block

    assert "formatDateBR" not in block


def test_receiving_payload_keeps_raw_iso_dates():
    source = read_app()

    start = source.index(
        "await this.api.registerReceive({"
    )

    end = source.index(
        "});",
        start,
    )

    block = source[start:end]

    assert (
        "manufacturing_date: manufacturingDate"
        in block
    )

    assert (
        "expiration_date: expirationDate"
        in block
    )

    assert "formatDateBR" not in block
