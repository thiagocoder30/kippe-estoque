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


def _compact(value: str) -> str:
    return "".join(
        value.split()
    )


def _method_block(
    start_marker: str,
    end_marker: str,
) -> str:
    start = APP.index(
        start_marker
    )

    end = APP.index(
        end_marker,
        start,
    )

    return APP[start:end]


def test_replenishment_unknown_product_has_explicit_state():
    assert (
        'id="replenishment-unknown-product-panel"'
        in INDEX
    )

    assert (
        "PRODUTO NÃO CADASTRADO"
        in INDEX
    )

    assert (
        'id="btn-replenishment-register-product"'
        in INDEX
    )


def test_unknown_product_is_not_added_to_cart():
    block = _compact(
        _method_block(
            "    async loadReplenishmentProduct(",
            "    renderReplenishmentCart() {",
        )
    )

    assert (
        "PRODUTO_NAO_CADASTRADO"
        in block
    )

    assert (
        "this.replenishmentProduct=null"
        in block
    )


def test_unknown_ean_can_open_canonical_product_registration():
    block = _compact(
        _method_block(
            "    bindReplenishmentModule() {",
            "    bindPutawayModule() {",
        )
    )

    assert (
        "btn-replenishment-register-product"
        in block
    )

    assert (
        "this.openNewProductRegistration("
        in block
    )


def test_replenishment_zero_stock_has_explicit_operator_state():
    assert (
        'id="replenishment-zero-stock-panel"'
        in INDEX
    )

    assert (
        "SEM ESTOQUE PARA ABASTECIMENTO"
        in INDEX
    )

    assert (
        "PODE AINDA ESTAR PRESENTE NA LOJA"
        in INDEX
    )


def test_product_query_quantity_is_used_for_zero_stock_guard():
    block = _compact(
        _method_block(
            "    async loadReplenishmentProduct(",
            "    renderReplenishmentCart() {",
        )
    )

    assert (
        "data.quantity"
        in block
    )

    assert (
        "Number(data.quantity"
        in block
    )


def test_zero_stock_does_not_make_product_eligible_for_cart():
    block = _compact(
        _method_block(
            "    async loadReplenishmentProduct(",
            "    renderReplenishmentCart() {",
        )
    )

    zero_guard = block.index(
        "Number(data.quantity"
    )

    product_assignment = block.index(
        "this.replenishmentProduct={"
    )

    assert (
        zero_guard
        <
        product_assignment
    )


def test_replenishment_does_not_create_store_quantity_semantics():
    combined = (
        INDEX + "\n" + APP
    ).lower()

    forbidden = [
        "store_quantity",
        "store_balance",
        "quantity_store",
        "saldo loja",
    ]

    for token in forbidden:
        assert token not in combined


def test_pick_plan_error_has_dedicated_operational_panel():
    assert (
        'id="replenishment-route-error-panel"'
        in INDEX
    )

    assert (
        'id="replenishment-route-error-product"'
        in INDEX
    )

    assert (
        'id="replenishment-route-error-batch"'
        in INDEX
    )


def test_unaddressed_fefo_error_keeps_cart_visible():
    block = _compact(
        _method_block(
            "    async startReplenishmentPick() {",
            "    renderReplenishmentPickStep() {",
        )
    )

    catch_start = block.index(
        "}catch(error){"
    )

    catch_section = block[
        catch_start:
    ]

    assert (
        "replenishment-cart-view"
        not in catch_section
        or
        "classList.add('hidden')"
        not in catch_section
    )


def test_unaddressed_fefo_error_is_translated_for_operator():
    block = _compact(
        _method_block(
            "    async startReplenishmentPick() {",
            "    renderReplenishmentPickStep() {",
        )
    )

    assert (
        "LOTE_FEFO_SEM_ENDERECAMENTO"
        in block
        or
        "LOTEFEFOSEMENDEREÇAMENTOFÍSICOPARACOLETA"
        in block
    )

    assert (
        "showReplenishmentRouteError"
        in block
    )


def test_route_error_does_not_mutate_cart():
    block = _compact(
        _method_block(
            "    async startReplenishmentPick() {",
            "    renderReplenishmentPickStep() {",
        )
    )

    catch_start = block.index(
        "}catch(error){"
    )

    catch_section = block[
        catch_start:
    ]

    assert (
        "this.replenishmentCart=[]"
        not in catch_section
    )

    assert (
        "this.replenishmentCart.splice"
        not in catch_section
    )
