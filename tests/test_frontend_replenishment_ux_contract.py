from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

INDEX = (
    ROOT / "web" / "index.html"
).read_text(
    encoding="utf-8"
)

APP = (
    ROOT / "web" / "js" / "app.js"
).read_text(
    encoding="utf-8"
)

API = (
    ROOT / "web" / "js" / "api.js"
).read_text(
    encoding="utf-8"
)

SCANNER = (
    ROOT / "web" / "js" / "scanner.js"
).read_text(
    encoding="utf-8"
)


def test_home_exposes_replenishment_module():
    assert 'id="btn-module-replenishment"' in INDEX
    assert "ABASTECER" in INDEX


def test_replenishment_has_dedicated_operational_view():
    assert 'id="replenishment-view"' in INDEX
    assert 'id="btn-back-replenishment"' in INDEX


def test_replenishment_supports_scanner_and_manual_identifier():
    assert 'id="replenishment-product-input"' in INDEX
    assert 'id="btn-replenishment-scanner"' in INDEX

    assert (
        "scannerTarget === 'replenishment'"
        in APP
    )

    assert (
        "this.scannerTarget = 'replenishment'"
        in APP
    )


def test_replenishment_reuses_canonical_product_query():
    assert (
        "this.api.queryProduct"
        in APP
    )

    assert (
        "replenishment"
        in APP.lower()
    )


def test_replenishment_has_identified_product_panel():
    required = [
        'id="replenishment-product-panel"',
        'id="replenishment-product-name"',
        'id="replenishment-product-sku"',
        'id="replenishment-product-ean"',
    ]

    for marker in required:
        assert marker in INDEX


def test_replenishment_has_positive_quantity_input():
    assert (
        'id="replenishment-quantity"'
        in INDEX
    )

    assert (
        'type="number"'
        in INDEX
    )

    assert (
        'id="btn-replenishment-add"'
        in INDEX
    )


def test_replenishment_has_cart_state_and_controls():
    required = [
        'id="replenishment-cart"',
        'id="replenishment-cart-empty"',
        'id="replenishment-cart-items"',
        'id="btn-replenishment-start-pick"',
    ]

    for marker in required:
        assert marker in INDEX

    assert (
        "replenishmentCart"
        in APP
    )


def test_api_client_exposes_replenishment_plan():
    assert (
        "planReplenishment"
        in API
    )

    assert (
        "/api/abastecimento/plano"
        in API
    )


def test_api_client_exposes_replenishment_pick_plan():
    assert (
        "planReplenishmentPick"
        in API
    )

    assert (
        "/api/abastecimento/coleta/plano"
        in API
    )


def test_api_client_exposes_replenishment_confirmation():
    assert (
        "confirmReplenishmentPick"
        in API
    )

    assert (
        "/api/abastecimento/coleta/confirmar"
        in API
    )


def test_frontend_asks_backend_for_physical_pick_plan():
    assert (
        "this.api.planReplenishmentPick"
        in APP
    )

    assert (
        "replenishmentPickSteps"
        in APP
    )


def test_pick_view_exposes_backend_route_fields():
    required = [
        'id="replenishment-pick-view"',
        'id="replenishment-pick-progress"',
        'id="replenishment-pick-location"',
        'id="replenishment-pick-product"',
        'id="replenishment-pick-sku"',
        'id="replenishment-pick-batch"',
        'id="replenishment-pick-expiration"',
        'id="replenishment-pick-planned-quantity"',
    ]

    for marker in required:
        assert marker in INDEX


def test_pick_view_uses_brazilian_date_formatter():
    assert (
        "formatDateBR"
        in APP
    )

    assert (
        "replenishment-pick-expiration"
        in APP
    )


def test_pick_confirmation_uses_actual_physical_quantity():
    assert (
        'id="replenishment-pick-confirmed-quantity"'
        in INDEX
    )

    assert (
        'id="btn-replenishment-confirm-pick"'
        in INDEX
    )

    assert (
        "this.api.confirmReplenishmentPick"
        in APP
    )


def test_frontend_does_not_create_store_balance_semantics():
    forbidden = [
        "store_quantity",
        "store_balance",
        "quantity_store",
    ]

    replenishment_code = (
        INDEX + "\n" + APP + "\n" + API
    ).lower()

    for token in forbidden:
        assert token not in replenishment_code


def test_frontend_does_not_modify_scanner_engine_for_replenishment():
    forbidden = [
        "replenishment",
        "abastecimento",
    ]

    scanner_lower = SCANNER.lower()

    for token in forbidden:
        assert token not in scanner_lower


def test_replenishment_has_completion_state():
    required = [
        'id="replenishment-success-panel"',
        "COLETA CONCLUÍDA",
    ]

    for marker in required:
        assert marker in INDEX


def test_replenishment_binding_is_bootstrapped():
    assert (
        "this.bindReplenishmentModule();"
        in APP
    )

    assert (
        "bindReplenishmentModule()"
        in APP
    )
