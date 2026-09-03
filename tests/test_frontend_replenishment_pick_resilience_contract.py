from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

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

    return APP[
        start:end
    ]


def test_partial_physical_confirmation_uses_actual_quantity():
    block = _compact(
        _method_block(
            "    async confirmReplenishmentPickStep() {",
            "    finishReplenishmentPick() {",
        )
    )

    assert (
        "constquantity=Number.parseInt("
        in block
    )

    assert (
        "quantity:quantity"
        in block
    )

    assert (
        "quantity:step.quantity"
        not in block
    )


def test_partial_confirmation_can_be_less_than_planned():
    block = _compact(
        _method_block(
            "    async confirmReplenishmentPickStep() {",
            "    finishReplenishmentPick() {",
        )
    )

    assert (
        "quantity>step.quantity"
        in block
    )

    assert (
        "quantity!==step.quantity"
        not in block
    )

    assert (
        "quantity<step.quantity"
        not in block
    )


def test_invalid_confirmation_does_not_call_backend():
    block = _compact(
        _method_block(
            "    async confirmReplenishmentPickStep() {",
            "    finishReplenishmentPick() {",
        )
    )

    invalid_guard = block.index(
        "if(!Number.isInteger(quantity)||quantity<=0)"
    )

    backend_call = block.index(
        "awaitthis.api.confirmReplenishmentPick("
    )

    assert invalid_guard < backend_call


def test_over_confirmation_does_not_call_backend():
    block = _compact(
        _method_block(
            "    async confirmReplenishmentPickStep() {",
            "    finishReplenishmentPick() {",
        )
    )

    over_guard = block.index(
        "if(quantity>step.quantity)"
    )

    backend_call = block.index(
        "awaitthis.api.confirmReplenishmentPick("
    )

    assert over_guard < backend_call


def test_pick_index_advances_only_after_successful_backend_confirmation():
    block = _compact(
        _method_block(
            "    async confirmReplenishmentPickStep() {",
            "    finishReplenishmentPick() {",
        )
    )

    backend_call = block.index(
        "awaitthis.api.confirmReplenishmentPick("
    )

    index_advance = block.index(
        "this.replenishmentPickIndex+=1"
    )

    catch_block = block.index(
        "}catch(error){"
    )

    assert (
        backend_call
        <
        index_advance
        <
        catch_block
    )


def test_backend_failure_does_not_advance_pick_index():
    block = _compact(
        _method_block(
            "    async confirmReplenishmentPickStep() {",
            "    finishReplenishmentPick() {",
        )
    )

    catch_start = block.index(
        "}catch(error){"
    )

    catch_section = block[
        catch_start:
    ]

    assert (
        "this.replenishmentPickIndex+="
        not in catch_section
    )

    assert (
        "this.replenishmentPickIndex++"
        not in catch_section
    )

    assert (
        "renderReplenishmentPickStep()"
        not in catch_section
    )


def test_backend_failure_surfaces_operational_error():
    block = _compact(
        _method_block(
            "    async confirmReplenishmentPickStep() {",
            "    finishReplenishmentPick() {",
        )
    )

    catch_start = block.index(
        "}catch(error){"
    )

    catch_section = block[
        catch_start:
    ]

    assert (
        "this.showReplenishmentPickError("
        in catch_section
    )


def test_completion_only_occurs_after_last_successful_step():
    block = _compact(
        _method_block(
            "    async confirmReplenishmentPickStep() {",
            "    finishReplenishmentPick() {",
        )
    )

    assert (
        "this.replenishmentPickIndex>=this.replenishmentPickSteps.length"
        in block
    )

    assert (
        "this.finishReplenishmentPick();"
        in block
    )


def test_pick_step_renders_planned_quantity_as_default_confirmation():
    block = _compact(
        _method_block(
            "    renderReplenishmentPickStep() {",
            "    async confirmReplenishmentPickStep() {",
        )
    )

    assert (
        "confirmed.value=String(step.quantity)"
        in block
    )

    assert (
        "confirmed.max=String(step.quantity)"
        in block
    )
