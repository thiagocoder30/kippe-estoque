from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]

INDEX = (
    ROOT
    / "web"
    / "index.html"
).read_text(
    encoding="utf-8"
)

APP = (
    ROOT
    / "web"
    / "js"
    / "app.js"
).read_text(
    encoding="utf-8"
)

API = (
    ROOT
    / "web"
    / "js"
    / "api.js"
).read_text(
    encoding="utf-8"
)


def _compact(value):
    return re.sub(
        r"\s+",
        "",
        value,
    )


def test_product_card_exposes_latest_receiving_summary():
    required_ids = (
        'id="product-audit-summary"',
        'id="product-audit-latest-receiving-date"',
        'id="product-audit-latest-receiving-supplier"',
        'id="product-audit-latest-receiving-document"',
        'id="product-audit-latest-receiving-batch"',
        'id="product-audit-latest-receiving-quantity"',
    )

    for marker in required_ids:
        assert marker in INDEX


def test_product_card_exposes_history_action():
    assert (
        'id="btn-product-audit-history"'
        in INDEX
    )

    assert (
        "VER HISTÓRICO"
        in INDEX
    )


def test_product_history_modal_is_mobile_first():
    required_ids = (
        'id="product-audit-history-modal"',
        'id="product-audit-history-title"',
        'id="product-audit-history-timeline"',
        'id="product-audit-history-empty"',
        'id="product-audit-history-error"',
        'id="btn-close-product-audit-history"',
    )

    for marker in required_ids:
        assert marker in INDEX

    modal_context = INDEX[
        INDEX.index(
            'id="product-audit-history-modal"'
        ):
    ]

    assert (
        "fixed inset-0"
        in modal_context
    )

    assert (
        "overflow-y-auto"
        in modal_context
        or
        "overflow-auto"
        in modal_context
    )


def test_history_api_client_uses_authenticated_002b_endpoint():
    compact = _compact(API)

    assert (
        "getProductHistory("
        in API
    )

    assert (
        "/api/products/"
        in API
    )

    assert (
        "/history"
        in API
    )

    assert (
        "method:'GET'"
        in compact
        or
        "method:\"GET\""
        in compact
    )


def test_product_search_loads_documentary_history():
    assert (
        "getProductHistory("
        in APP
    )

    assert (
        "loadProductAuditHistory"
        in APP
        or
        "loadProductHistory"
        in APP
    )


def test_latest_receiving_summary_uses_api_latest_receiving():
    compact = _compact(APP)

    assert (
        "latest_receiving"
        in APP
    )

    required_documentary_fields = (
        "supplier",
        "document_id",
        "batch_code",
        "quantity_actual",
        "occurred_at",
    )

    for field in required_documentary_fields:
        assert field in APP

    assert (
        "latest_receiving"
        in compact
    )


def test_product_history_timeline_supports_lifecycle_event_types():
    required_event_types = (
        "RECEBIMENTO",
        "PUTAWAY",
        "ABASTECIMENTO_LOJA",
    )

    for event_type in required_event_types:
        assert event_type in APP


def test_receiving_timeline_exposes_documentary_context():
    required_fields = (
        "supplier",
        "document_id",
        "origin_document",
        "batch_code",
        "quantity_actual",
        "operator_id",
        "occurred_at",
    )

    for field in required_fields:
        assert field in APP


def test_putaway_timeline_exposes_location_context():
    assert (
        "location_id"
        in APP
    )

    assert (
        "PUTAWAY"
        in APP
    )


def test_replenishment_timeline_exposes_quantity_and_divergence_context():
    required_fields = (
        "quantity_planned",
        "quantity_actual",
        "quantity_divergence",
        "location_id",
        "batch_code",
        "operator_id",
        "occurred_at",
    )

    for field in required_fields:
        assert field in APP

    assert (
        "ABASTECIMENTO_LOJA"
        in APP
    )


def test_history_has_explicit_empty_state():
    assert (
        'id="product-audit-history-empty"'
        in INDEX
    )

    assert (
        "SEM HISTÓRICO"
        in INDEX
        or
        "NENHUM HISTÓRICO"
        in INDEX
        or
        "AINDA NÃO HÁ"
        in INDEX
    )


def test_history_has_explicit_error_state():
    assert (
        'id="product-audit-history-error"'
        in INDEX
    )

    assert (
        "showProductAuditHistoryError"
        in APP
        or
        "showProductHistoryError"
        in APP
    )


def test_history_modal_can_be_closed_without_mutating_stock():
    assert (
        'id="btn-close-product-audit-history"'
        in INDEX
    )

    compact = _compact(APP)

    assert (
        "btn-close-product-audit-history"
        in APP
    )

    assert (
        "product-audit-history-modal"
        in APP
    )

    forbidden = (
        "confirmReplenishmentPick(",
        "receiveProduct(",
        "putawayProduct(",
    )

    history_candidates = (
        "openProductAuditHistory",
        "renderProductAuditHistory",
        "loadProductAuditHistory",
        "openProductHistory",
        "renderProductHistory",
        "loadProductHistory",
    )

    blocks = []

    for name in history_candidates:
        position = APP.find(name)

        if position >= 0:
            blocks.append(
                APP[
                    position:
                    position + 12000
                ]
            )

    combined = "\n".join(blocks)

    assert combined

    for marker in forbidden:
        assert marker not in combined


def test_history_does_not_derive_current_stock_from_audit_events():
    compact = _compact(APP)

    forbidden_patterns = (
        "events.reduce(",
        "history.reduce(",
        "auditEvents.reduce(",
        "quantity_after-quantity_before",
        "quantity_before+quantity_actual",
        "quantity_before-quantity_actual",
    )

    for pattern in forbidden_patterns:
        assert pattern not in compact


def test_history_does_not_claim_invoice_attachment_capability():
    forbidden_claims = (
        "VER ANEXO DA NF",
        "ABRIR ANEXO DA NF",
        "BAIXAR NOTA FISCAL",
        "VISUALIZAR NOTA FISCAL",
        "ANEXO DISPONÍVEL",
    )

    combined = (
        INDEX
        + "\n"
        + APP
    ).upper()

    for claim in forbidden_claims:
        assert claim not in combined
