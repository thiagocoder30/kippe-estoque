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


def test_completion_has_explicit_partial_divergence_state():
    assert (
        'id="replenishment-completion-divergence"'
        in INDEX
    )

    assert (
        "COLETA CONCLUÍDA COM DIVERGÊNCIA"
        in INDEX
    )


def test_completion_exposes_planned_confirmed_and_missing_quantities():
    required_ids = [
        'id="replenishment-completion-planned"',
        'id="replenishment-completion-confirmed"',
        'id="replenishment-completion-missing"',
    ]

    for marker in required_ids:
        assert marker in INDEX

    assert "PLANEJADO" in INDEX
    assert "COLETADO" in INDEX
    assert "NÃO ENCONTRADO" in INDEX


def test_completion_exposes_product_batch_and_location():
    required_ids = [
        'id="replenishment-completion-product"',
        'id="replenishment-completion-batch"',
        'id="replenishment-completion-location"',
    ]

    for marker in required_ids:
        assert marker in INDEX


def test_partial_confirmation_is_detected_from_planned_and_actual():
    block = _compact(
        _method_block(
            "    async confirmReplenishmentPickStep() {",
            "    finishReplenishmentPick() {",
        )
    )

    assert (
        "plannedQuantity"
        in block
    )

    assert (
        "actualQuantity"
        in block
    )

    assert (
        "actualQuantity<plannedQuantity"
        in block
        or
        "actualQuantity!==plannedQuantity"
        in block
    )


def test_missing_quantity_is_derived_not_manually_entered():
    combined = _compact(
        APP
    )

    assert (
        "plannedQuantity-actualQuantity"
        in combined
        or
        "Math.max(0,plannedQuantity-actualQuantity)"
        in combined
    )


def test_partial_confirmation_keeps_backend_quantity_as_actual():
    block = _compact(
        _method_block(
            "    async confirmReplenishmentPickStep() {",
            "    finishReplenishmentPick() {",
        )
    )

    assert (
        "quantity:actualQuantity"
        in block
    )


def test_partial_completion_preserves_confirmation_context():
    assert (
        "replenishmentCompletion"
        in APP
        or
        "replenishmentLastConfirmation"
        in APP
    )


def test_partial_completion_does_not_create_store_balance():
    combined = (
        INDEX +
        "\n" +
        APP
    ).lower()

    forbidden = [
        "store_quantity",
        "store_balance",
        "quantity_store",
        "saldo loja",
    ]

    for token in forbidden:
        assert token not in combined


def test_partial_completion_explains_only_confirmed_quantity_was_deducted():
    assert (
        "FORAM BAIXADAS DO ESTOQUE CONTROLADO"
        in INDEX
        or
        "FOI BAIXADA DO ESTOQUE CONTROLADO"
        in INDEX
    )


def test_partial_completion_explains_missing_quantity_was_not_found():
    assert (
        "NÃO FOI LOCALIZADA"
        in INDEX
        or
        "NÃO FORAM LOCALIZADAS"
        in INDEX
    )


def test_normal_completion_state_is_still_supported():
    assert (
        "COLETA CONCLUÍDA"
        in INDEX
    )


def test_completion_only_happens_after_successful_backend_confirmation():
    block = _compact(
        _method_block(
            "    async confirmReplenishmentPickStep() {",
            "    finishReplenishmentPick() {",
        )
    )

    backend_call = block.index(
        "confirmReplenishmentPick("
    )

    assert (
        "finishReplenishmentPick("
        in block
    )

    finish_call = block.rindex(
        "finishReplenishmentPick("
    )

    assert backend_call < finish_call
