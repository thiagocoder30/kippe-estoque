from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_app() -> str:
    return (
        ROOT / "web/js/app.js"
    ).read_text(
        encoding="utf-8"
    )


def read_html() -> str:
    return (
        ROOT / "web/index.html"
    ).read_text(
        encoding="utf-8"
    )


def compact(text: str) -> str:
    return "".join(
        text.split()
    )


def method_block(
    source: str,
    start_marker: str,
    end_marker: str,
) -> str:
    start = source.index(
        start_marker
    )

    end = source.index(
        end_marker,
        start,
    )

    return source[
        start:end
    ]


def inbound_block() -> str:
    return method_block(
        read_app(),
        "    bindInboundModule()",
        "    bindPutawayModule()",
    )


def putaway_block() -> str:
    return method_block(
        read_app(),
        "    bindPutawayModule()",
        "    bindReportsModule()",
    )


def test_product_registration_success_is_a_dedicated_modal():
    html = read_html()

    assert (
        'id="new-product-success-modal"'
        in html
    )

    assert (
        "PRODUTO CADASTRADO"
        in html
    )

    assert (
        'id="continue-new-product-receiving"'
        in html
    )


def test_product_success_modal_exposes_created_identity():
    html = read_html()

    required_ids = (
        "new-product-success-name",
        "new-product-success-sku",
        "new-product-success-ean",
    )

    for element_id in required_ids:
        assert (
            f'id="{element_id}"'
            in html
        )


def test_continue_after_product_registration_preserves_receiving_context():
    source = inbound_block()

    start = source.index(
        "'continue-new-product-receiving'"
    )

    end = source.index(
        "'btn-module-inbound'",
        start,
    )

    continuation = source[
        start:end
    ]

    assert (
        "resetReceivingForm"
        not in continuation
    )

    assert (
        "this.loadReceivingProduct"
        in continuation
    )


def test_receiving_success_is_a_dedicated_modal():
    html = read_html()

    assert (
        'id="receive-success-modal"'
        in html
    )

    assert (
        "RECEBIMENTO REALIZADO"
        in html
    )


def test_receiving_success_modal_has_assisted_putaway_actions():
    html = read_html()

    assert (
        'id="btn-receive-putaway-now"'
        in html
    )

    assert (
        'id="btn-receive-putaway-later"'
        in html
    )

    assert (
        "ENDEREÇAR AGORA"
        in html
        or
        "ENDERECAR AGORA"
        in html
    )

    assert (
        "ENDEREÇAR DEPOIS"
        in html
        or
        "ENDERECAR DEPOIS"
        in html
    )


def test_successful_receiving_stores_exact_new_receiving_context():
    source = inbound_block()
    normalized = compact(source)

    assert (
        "this.lastReceivingResult=receiving"
        in normalized
        or
        "this.assistedReceiving=receiving"
        in normalized
    )


def test_putaway_now_uses_exact_received_sku_and_batch():
    source = read_app()
    normalized = compact(source)

    assert (
        "'btn-receive-putaway-now'"
        in source
    )

    assert (
        ".batch_code"
        in source
    )

    assert (
        ".sku"
        in source
    )

    assert (
        "openAssistedPutaway"
        in source
        or
        "openReceivingPutaway"
        in source
    )

    assert (
        "batchCode"
        in source
        or
        "preferredBatchCode"
        in source
    )

    assert (
        "this.lastReceivingResult"
        in source
        or
        "this.assistedReceiving"
        in source
    )


def test_assisted_putaway_can_select_preferred_exact_batch():
    source = putaway_block()

    assert (
        "preferredBatchCode"
        in source
        or
        "requiredBatchCode"
        in source
    )

    assert (
        ".find("
        in source
    )

    assert (
        "batch.code"
        in source
    )


def test_manual_putaway_keeps_fefo_default_for_pending_batches():
    source = putaway_block()

    assert (
        "pendingBatches"
        in source
    )

    assert (
        ".sort("
        in source
    )

    assert (
        "expiration_date"
        in source
    )


def test_assisted_putaway_does_not_ask_operator_to_reidentify_product():
    html = read_html()
    source = read_app()

    assert (
        "assisted-putaway"
        in source.lower()
        or
        "receiving-putaway"
        in source.lower()
    )

    assert (
        "readonly"
        in html[
            html.index(
                'id="put-ean"'
            ) - 250:
            html.index(
                'id="put-ean"'
            ) + 350
        ]
        or
        "disabled"
        in html[
            html.index(
                'id="put-ean"'
            ) - 250:
            html.index(
                'id="put-ean"'
            ) + 350
        ]
        or
        "setAttribute('readonly'"
        in source
        or
        'setAttribute("readonly"'
        in source
    )


def test_assisted_putaway_batch_remains_readonly():
    html = read_html()

    batch_position = html.index(
        'id="put-batch"'
    )

    batch_context = html[
        batch_position - 300:
        batch_position + 400
    ]

    assert (
        "readonly"
        in batch_context
    )


def test_putaway_success_primary_action_is_finalize():
    html = read_html()

    assert (
        'id="btn-putaway-success-finalize"'
        in html
    )

    assert (
        "FINALIZAR"
        in html
    )


def test_assisted_putaway_finalize_returns_to_home():
    source = putaway_block()

    assert (
        "'btn-putaway-success-finalize'"
        in source
    )

    assert (
        "'home-module-view'"
        in source
    )

    assert (
        ".classList.remove("
        in source
    )


def test_putaway_later_returns_home_without_putaway_mutation():
    source = inbound_block()

    start = source.index(
        "'btn-receive-putaway-later'"
    )

    end = len(source)

    later_block = source[
        start:end
    ]

    assert (
        "registerPutaway"
        not in later_block
    )

    assert (
        "'home-module-view'"
        in later_block
    )


def test_assisted_flow_clears_receiving_state_only_after_completion():
    source = read_app()
    normalized = compact(source)

    assert (
        "resetReceivingForm()"
        in source
    )

    assert (
        "lastReceivingResult=null"
        in normalized
        or
        "assistedReceiving=null"
        in normalized
    )


def test_scanner_manager_is_not_replaced_by_receiving_ux_002():
    scanner = (
        ROOT / "web/js/scanner.js"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "class ScannerManager"
        in scanner
    )

    assert (
        "Html5Qrcode"
        in scanner
    )

    assert (
        "Html5Qrcode.getCameras"
        in scanner
    )

    assert (
        "kippe.scanner.preferredCameraId"
        in scanner
    )

    # Comentários documentais podem mencionar engines removidos.
    # O contrato proíbe somente sua implementação executável.
    forbidden_runtime_tokens = (
        "new BarcodeDetector(",
        "BarcodeDetector.getSupportedFormats",
        "new Quagga",
        "Quagga.init(",
        "Quagga.decodeSingle(",
    )

    for token in forbidden_runtime_tokens:
        assert token not in scanner
