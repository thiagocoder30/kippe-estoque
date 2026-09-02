from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_app() -> str:
    return (ROOT / "web/js/app.js").read_text()


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


def reset_block() -> str:
    source = read_app()

    return method_block(
        source,
        "    resetReceivingForm()",
        "    bindReceivingDetailedControls()",
    )


def inbound_block() -> str:
    source = read_app()

    return method_block(
        source,
        "    bindInboundModule()",
        "    bindPutawayModule()",
    )


def test_receiving_has_canonical_reset_method():
    source = read_app()

    assert "resetReceivingForm()" in source


def test_receiving_reset_has_generic_value_clearer():
    source = compact(reset_block())

    assert (
        "constsetValue=(id,value='')=>"
        in source
    )

    assert (
        "document.getElementById(id)"
        in source
    )

    assert (
        "element.value=value"
        in source
    )


def test_receiving_reset_clears_business_inputs():
    source = compact(reset_block())

    required_ids = (
        "rec-ean",
        "rec-batch",
        "rec-manufacturing",
        "rec-expiration",
        "rec-supplier",
        "rec-invoice",
        "rec-qty",
        "rec-units-per-package",
        "rec-package-qty",
    )

    for field_id in required_ids:
        assert (
            f"setValue('{field_id}')"
            in source
        )


def test_receiving_reset_restores_manual_origin():
    source = compact(reset_block())

    assert (
        "document.getElementById('rec-origin')"
        in source
    )

    assert (
        ".value='MANUAL'"
        in source
        or
        '.value="MANUAL"'
        in source
    )


def test_receiving_reset_restores_unit_entry_mode():
    source = compact(reset_block())

    assert (
        "document.getElementById('rec-entry-mode-unit')"
        in source
    )

    assert (
        ".checked=true"
        in source
    )

    assert (
        "document.getElementById('rec-entry-mode-package')"
        in source
    )

    assert (
        ".checked=false"
        in source
    )


def test_receiving_reset_clears_product_identification():
    source = compact(reset_block())

    assert (
        "setValue('rec-product-description')"
        in source
    )

    required_text_ids = (
        "receive-product-name",
        "receive-product-sku",
        "receive-product-ean",
        "receive-product-unit",
    )

    for field_id in required_text_ids:
        assert (
            f"setText('{field_id}')"
            in source
        )

    assert (
        "hide('receive-product-card')"
        in source
    )


def test_receiving_reset_hides_previous_success():
    source = compact(reset_block())

    assert (
        "hide('receive-success-panel')"
        in source
    )


def test_receiving_reset_refreshes_derived_state():
    source = reset_block()

    assert (
        "this.updateReceivingExpirationIntelligence()"
        in source
    )

    assert (
        "this.updateReceivingQuantityMode()"
        in source
        or
        "this.calculateReceivingTotalUnits()"
        in source
    )

    assert (
        "this.updateReceivingSummary()"
        in source
    )


def test_new_traditional_receiving_starts_with_reset():
    source = inbound_block()

    traditional_start = source.index(
        "'btn-inbound-traditional'"
    )

    scanner_start = source.index(
        "'btn-receive-scanner'",
        traditional_start,
    )

    traditional_block = source[
        traditional_start:scanner_start
    ]

    assert (
        "this.resetReceivingForm()"
        in traditional_block
    )


def test_new_product_continue_does_not_reset_active_receiving():
    source = inbound_block()

    start = source.index(
        "'continue-new-product-receiving'"
    )

    end = source.index(
        "'btn-module-inbound'",
        start,
    )

    continuation_block = source[start:end]

    assert (
        "this.resetReceivingForm()"
        not in continuation_block
    )

    assert (
        "this.loadReceivingProduct"
        in continuation_block
    )


def test_receiving_scanner_return_does_not_reset_active_receiving():
    source = read_app()

    scanner_receive_start = source.index(
        "if (this.scannerTarget === 'receive')"
    )

    scanner_receive_end = source.index(
        "this.scannerTarget = 'search'",
        scanner_receive_start,
    )

    scanner_receive_block = source[
        scanner_receive_start:
        scanner_receive_end
    ]

    assert (
        "resetReceivingForm"
        not in scanner_receive_block
    )

    assert (
        "this.loadReceivingProduct"
        in scanner_receive_block
    )
