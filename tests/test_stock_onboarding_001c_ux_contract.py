from pathlib import Path


INDEX = Path("web/index.html")
APP = Path("web/js/app.js")
API = Path("web/js/api.js")
SCANNER = Path("web/js/scanner.js")


def _html():
    return INDEX.read_text(
        encoding="utf-8"
    )


def _app():
    return APP.read_text(
        encoding="utf-8"
    )


def _api():
    return API.read_text(
        encoding="utf-8"
    )


def test_api_client_exposes_existing_stock_onboarding():
    source = _api()

    assert (
        "async onboardExistingStock("
        in source
    )

    assert (
        "/api/stock/onboarding"
        in source
    )


def test_api_client_uses_post_for_existing_stock_onboarding():
    source = _api()

    start = source.index(
        "async onboardExistingStock("
    )

    region = source[
        start:start + 900
    ]

    assert (
        "/api/stock/onboarding"
        in region
    )

    assert (
        "method: 'POST'"
        in region
        or 'method: "POST"'
        in region
    )

    assert (
        "JSON.stringify(payload)"
        in region
    )


def test_new_product_success_has_two_explicit_business_actions():
    html = _html()

    assert (
        'id="continue-new-product-receiving"'
        in html
    )

    assert (
        'id="continue-new-product-existing-stock"'
        in html
    )

    assert (
        "RECEBER MERCADORIA"
        in html
    )

    assert (
        "CADASTRAR ESTOQUE JÁ EXISTENTE"
        in html
    )


def test_existing_stock_is_not_implemented_as_receiving_checkbox():
    html = _html().lower()

    forbidden = (
        'type="checkbox"'
        ' name="existing-stock"',
        'type="checkbox"'
        ' id="existing-stock"',
        'type="checkbox"'
        ' id="legacy-stock"',
    )

    for marker in forbidden:
        assert marker not in html


def test_onboarding_has_dedicated_modal():
    html = _html()

    assert (
        'id="existing-stock-modal"'
        in html
    )

    assert (
        "IMPLANTAÇÃO DE ESTOQUE EXISTENTE"
        in html
    )

    assert (
        'aria-label="Implantação de estoque existente"'
        in html
    )


def test_onboarding_modal_identifies_product():
    html = _html()

    required = (
        'id="existing-stock-product-name"',
        'id="existing-stock-product-sku"',
        'id="existing-stock-product-ean"',
    )

    for marker in required:
        assert marker in html


def test_onboarding_form_exposes_physical_count():
    html = _html()

    assert (
        'id="existing-stock-quantity"'
        in html
    )

    assert (
        "CONTAGEM FÍSICA"
        in html
    )


def test_onboarding_form_exposes_required_batch_and_expiration():
    html = _html()

    assert (
        'id="existing-stock-batch"'
        in html
    )

    assert (
        'id="existing-stock-expiration"'
        in html
    )


def test_onboarding_form_exposes_optional_traceability_fields():
    html = _html()

    required = (
        'id="existing-stock-manufacturing"',
        'id="existing-stock-location"',
        'id="existing-stock-supplier"',
        'id="existing-stock-document"',
    )

    for marker in required:
        assert marker in html


def test_onboarding_form_exposes_optional_historical_date():
    html = _html()

    assert (
        'id="existing-stock-historical-date"'
        in html
    )

    assert (
        'type="date"'
        in html
    )


def test_onboarding_form_exposes_historical_basis():
    html = _html()

    assert (
        'id="existing-stock-historical-basis"'
        in html
    )

    assert (
        'value="DOCUMENT"'
        in html
    )

    assert (
        'value="OPERATOR_DECLARATION"'
        in html
    )


def test_historical_date_has_truth_warning():
    html = _html()

    assert (
        "Informar somente quando houver"
        in html
        or
        "Informe somente quando houver"
        in html
    )

    assert (
        "deixar"
        in html.lower()
        and
        "vazi"
        in html.lower()
    )


def test_historical_date_has_no_today_default_in_html():
    html = _html()

    marker = (
        'id="existing-stock-historical-date"'
    )

    start = html.index(
        marker
    )

    region = html[
        max(0, start - 300):
        start + 600
    ]

    assert (
        'value="202'
        not in region
    )


def test_historical_basis_starts_without_claiming_evidence():
    html = _html()

    marker = (
        'id="existing-stock-historical-basis"'
    )

    start = html.index(
        marker
    )

    region = html[
        start:start + 1000
    ]

    assert (
        'value=""'
        in region
    )


def test_onboarding_has_explicit_submit_action():
    html = _html()

    assert (
        'id="submit-existing-stock"'
        in html
    )

    assert (
        "INCORPORAR ESTOQUE EXISTENTE"
        in html
    )


def test_onboarding_has_dedicated_error_panel():
    html = _html()

    assert (
        'id="existing-stock-error"'
        in html
    )


def test_onboarding_has_dedicated_success_state():
    html = _html()

    assert (
        'id="existing-stock-success-modal"'
        in html
    )

    assert (
        "ESTOQUE EXISTENTE INCORPORADO"
        in html
    )

    assert (
        "CONTAGEM FÍSICA"
        in html
    )


def test_success_does_not_claim_new_receiving():
    html = _html()

    marker = (
        'id="existing-stock-success-modal"'
    )

    start = html.index(
        marker
    )

    region = html[
        start:start + 3000
    ]

    assert (
        "RECEBIMENTO REALIZADO"
        not in region
    )

    assert (
        "MERCADORIA RECEBIDA"
        not in region
    )


def test_application_keeps_target_product_state():
    source = _app()

    assert (
        "this.existingStockProduct"
        in source
    )


def test_application_exposes_management_role_guard():
    source = _app()

    assert (
        "canManageExistingStock"
        in source
    )

    assert (
        "GERENTE"
        in source
    )

    assert (
        "ADMIN_SISTEMA"
        in source
    )


def test_operator_role_is_not_treated_as_management_role():
    source = _app()

    marker = (
        "canManageExistingStock"
    )

    start = source.index(
        marker
    )

    region = source[
        start:start + 1800
    ]

    assert (
        "GERENTE"
        in region
    )

    assert (
        "ADMIN_SISTEMA"
        in region
    )

    assert not (
        "role === 'OPERADOR'"
        in region
    )


def test_application_can_open_existing_stock_for_product():
    source = _app()

    assert (
        "openExistingStockOnboarding"
        in source
    )

    marker = (
        "openExistingStockOnboarding"
    )

    start = source.index(
        marker
    )

    region = source[
        start:start + 3000
    ]

    assert (
        "existing-stock-modal"
        in region
    )

    assert (
        "existingStockProduct"
        in region
    )


def test_new_product_existing_stock_action_uses_created_product_context():
    source = _app()

    assert (
        "continue-new-product-existing-stock"
        in source
    )

    assert (
        "openExistingStockOnboarding"
        in source
    )


def test_existing_catalog_product_has_onboarding_action():
    html = _html()
    source = _app()

    assert (
        'id="btn-existing-stock-onboarding"'
        in html
    )

    assert (
        "btn-existing-stock-onboarding"
        in source
    )

    assert (
        "openExistingStockOnboarding"
        in source
    )


def test_existing_catalog_action_is_management_controlled():
    source = _app()

    assert (
        "btn-existing-stock-onboarding"
        in source
    )

    assert (
        "canManageExistingStock"
        in source
    )


def test_onboarding_submit_calls_only_onboarding_api():
    source = _app()

    marker = (
        "submit-existing-stock"
    )

    start = source.index(
        marker
    )

    region = source[
        start:start + 7000
    ]

    assert (
        "onboardExistingStock"
        in region
    )

    assert (
        "registerReceive("
        not in region
    )


def test_onboarding_payload_contains_canonical_fields():
    source = _app()

    marker = (
        "onboardExistingStock"
    )

    start = source.index(
        marker
    )

    region = source[
        max(
            0,
            start - 4500,
        ):
        start + 2500
    ]

    required = (
        "sku",
        "quantity",
        "batch_code",
        "expiration_date",
        "manufacturing_date",
        "supplier",
        "location_id",
        "historical_receipt_date",
        "historical_date_basis",
        "document_id",
    )

    for field in required:
        assert field in region


def test_historical_date_is_reset_to_empty_string():
    source = _app()

    assert (
        "existing-stock-historical-date"
        in source
    )

    marker = (
        "existing-stock-historical-date"
    )

    hits = []

    offset = 0

    while True:
        index = source.find(
            marker,
            offset,
        )

        if index == -1:
            break

        hits.append(
            index
        )

        offset = (
            index
            + len(marker)
        )

    assert hits

    regions = [
        source[
            max(
                0,
                index - 800,
            ):
            index + 1200
        ]
        for index in hits
    ]

    assert any(
        (
            ".value = ''"
            in region
            or
            ".value = \"\""
            in region
        )
        for region in regions
    )


def test_historical_basis_is_reset_to_empty_string():
    source = _app()

    marker = (
        "existing-stock-historical-basis"
    )

    assert marker in source

    positions = []

    offset = 0

    while True:
        index = source.find(
            marker,
            offset,
        )

        if index == -1:
            break

        positions.append(
            index
        )

        offset = (
            index
            + len(marker)
        )

    regions = [
        source[
            max(
                0,
                index - 800,
            ):
            index + 1200
        ]
        for index in positions
    ]

    assert any(
        (
            ".value = ''"
            in region
            or
            ".value = \"\""
            in region
        )
        for region in regions
    )


def test_document_basis_has_frontend_consistency_validation():
    source = _app()

    assert (
        "DOCUMENT"
        in source
    )

    assert (
        "historical"
        in source.lower()
    )

    assert (
        "document"
        in source.lower()
    )


def test_existing_receiving_action_remains_present():
    html = _html()
    source = _app()

    assert (
        'id="continue-new-product-receiving"'
        in html
    )

    assert (
        "continue-new-product-receiving"
        in source
    )

    assert (
        "loadReceivingProduct("
        in source
    )


def test_receiving_modal_semantics_remain_explicit():
    html = _html()

    assert (
        "RECEBIMENTO • NOVA ENTRADA"
        in html
    )

    assert (
        "RECEBIMENTO DE MERCADORIA"
        in html
    )


def test_onboarding_does_not_reuse_receive_form_ids():
    html = _html()

    required = (
        'id="existing-stock-quantity"',
        'id="existing-stock-batch"',
        'id="existing-stock-expiration"',
    )

    for marker in required:
        assert marker in html

    assert (
        'id="rec-qty"'
        in html
    )

    assert (
        'id="rec-batch"'
        in html
    )


def test_timeline_specific_implantacao_rendering_is_deferred():
    source = _app()

    marker = (
        "const typeConfig = {"
    )

    assert marker in source

    start = source.index(
        marker
    )

    region = source[
        start:start + 1600
    ]

    assert (
        "RECEBIMENTO"
        in region
    )

    assert (
        "PUTAWAY"
        in region
    )

    assert (
        "ABASTECIMENTO_LOJA"
        in region
    )

    assert (
        "IMPLANTACAO_ESTOQUE"
        not in region
    )


def test_scanner_source_has_no_existing_stock_target():
    source = SCANNER.read_text(
        encoding="utf-8"
    )

    assert (
        "existing-stock"
        not in source
    )

    assert (
        "stock-onboarding"
        not in source
    )
