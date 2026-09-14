from pathlib import Path
import re


HTML_PATH = Path("web/index.html")
APP_PATH = Path("web/js/app.js")


def html():
    return HTML_PATH.read_text(
        encoding="utf-8"
    )


def app():
    return APP_PATH.read_text(
        encoding="utf-8"
    )


def button_tag(source, element_id):
    pattern = re.compile(
        rf'<button\b'
        rf'(?=[^>]*id="{re.escape(element_id)}")'
        rf'[^>]*>',
        re.DOTALL,
    )

    match = pattern.search(source)

    assert match, (
        f"button not found: {element_id}"
    )

    return match.group(0)


def classes(tag):
    match = re.search(
        r'class="([^"]*)"',
        tag,
        re.DOTALL,
    )

    assert match

    return set(
        match.group(1).split()
    )


def test_post_create_has_two_explicit_decision_actions():
    source = html()

    assert (
        'id="continue-new-product-receiving"'
        in source
    )

    assert (
        'id="continue-new-product-existing-stock"'
        in source
    )

    assert "RECEBER MERCADORIA" in source
    assert (
        "CADASTRAR ESTOQUE JÁ EXISTENTE"
        in source
    )


def test_receive_action_has_its_own_arrival_now_explanation():
    source = html()

    assert (
        'id="new-product-receiving-explanation"'
        in source
    )

    marker = (
        'id="new-product-receiving-explanation"'
    )

    start = source.index(marker)

    region = source[
        start:start + 800
    ].lower()

    assert "chegando" in region
    assert "agora" in region


def test_existing_stock_action_has_its_own_preexisting_explanation():
    source = html()

    assert (
        'id="new-product-existing-stock-explanation"'
        in source
    )

    marker = (
        'id="new-product-existing-stock-explanation"'
    )

    start = source.index(marker)

    region = source[
        start:start + 900
    ].lower()

    assert "já estava" in region
    assert "estoque" in region
    assert "kippe" in region


def test_receive_explanation_is_not_shared_with_existing_stock():
    source = html()

    receive_button = source.index(
        'id="continue-new-product-receiving"'
    )

    existing_button = source.index(
        'id="continue-new-product-existing-stock"'
    )

    receive_explanation = source.index(
        'id="new-product-receiving-explanation"'
    )

    existing_explanation = source.index(
        'id="new-product-existing-stock-explanation"'
    )

    assert (
        receive_button
        < receive_explanation
        < existing_button
        < existing_explanation
    )


def test_post_create_existing_stock_visibility_is_refreshed_after_auth():
    source = app()

    assignments = list(
        re.finditer(
            r"this\.currentOperator\s*=\s*([^;]+);",
            source,
        )
    )

    authenticated_assignments = []

    for match in assignments:
        value = match.group(1).strip()

        if value == "null":
            continue

        authenticated_assignments.append(
            match
        )

    assert authenticated_assignments, (
        "No authenticated currentOperator "
        "assignment found."
    )

    assert any(
        "this.updateExistingStockActionVisibility()"
        in source[
            match.end():
            match.end() + 1200
        ]
        for match in authenticated_assignments
    ), (
        "Existing-stock action visibility must "
        "be refreshed after authenticated "
        "operator state is established."
    )


def test_post_create_existing_stock_button_remains_management_controlled():
    source = app()

    assert "canManageExistingStock" in source
    assert "GERENTE" in source
    assert "ADMIN_SISTEMA" in source

    marker = (
        "updateExistingStockActionVisibility()"
    )

    assert marker in source

    assert (
        "continue-new-product-existing-stock"
        in source
    )


def test_card_existing_stock_button_matches_history_control_size():
    source = html()

    history = classes(
        button_tag(
            source,
            "btn-product-audit-history",
        )
    )

    onboarding = classes(
        button_tag(
            source,
            "btn-existing-stock-onboarding",
        )
    )

    sizing_contract = {
        "w-full",
        "rounded-lg",
        "px-3",
        "py-2.5",
        "text-[10px]",
        "font-black",
        "tracking-wider",
        "active:scale-[0.98]",
    }

    assert sizing_contract <= history
    assert sizing_contract <= onboarding


def test_card_existing_stock_button_keeps_semantic_orange_color():
    source = html()

    onboarding = classes(
        button_tag(
            source,
            "btn-existing-stock-onboarding",
        )
    )

    assert "bg-amber-600" in onboarding


def test_history_button_keeps_blue_semantic_color():
    source = html()

    history = classes(
        button_tag(
            source,
            "btn-product-audit-history",
        )
    )

    assert "bg-[#124191]" in history


def test_post_create_receive_button_keeps_blue_and_existing_stock_orange():
    source = html()

    receive = classes(
        button_tag(
            source,
            "continue-new-product-receiving",
        )
    )

    existing = classes(
        button_tag(
            source,
            "continue-new-product-existing-stock",
        )
    )

    assert "bg-[#124191]" in receive
    assert "bg-amber-600" in existing


def test_existing_stock_decision_is_not_a_checkbox():
    source = html().lower()

    post_create_start = source.index(
        'id="new-product-success-modal"'
    )

    post_create_end = source.index(
        "<!-- stock-onboarding-001c",
        post_create_start,
    )

    region = source[
        post_create_start:
        post_create_end
    ]

    assert 'type="checkbox"' not in region


def test_receiving_binding_remains_separate_from_onboarding_binding():
    source = app()

    receiving = source.index(
        "'continue-new-product-receiving'"
    )

    onboarding = source.index(
        "'continue-new-product-existing-stock'"
    )

    assert receiving != onboarding

    onboarding_region = source[
        onboarding:
        onboarding + 2500
    ]

    assert (
        "openExistingStockOnboarding"
        in onboarding_region
    )

    assert (
        "loadReceivingProduct"
        not in onboarding_region
    )


def test_original_001c_business_warning_remains_present():
    source = html().lower()

    assert (
        "não representa uma nova chegada "
        "de mercadoria"
        in source
    )

    assert "contagem física" in source
