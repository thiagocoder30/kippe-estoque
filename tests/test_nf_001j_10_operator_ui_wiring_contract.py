"""
NF-001J.10 — Operator UI Wiring Contract.

The frontend must:
- reuse the existing Kippe application;
- preserve manual receiving;
- expose documentary invoice reconciliation;
- require explicit physical conference;
- block unresolved product lines;
- execute only through the J.9 certified endpoint;
- surface divergence and replay/execution feedback;
- prevent accidental duplicate submission.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative):
    return (
        ROOT / relative
    ).read_text(
        encoding="utf-8"
    )


def test_nf001j10_reuses_existing_inbound_application():
    html = _read("web/index.html")

    assert 'id="btn-inbound-traditional"' in html
    assert 'id="btn-inbound-ai"' in html
    assert 'id="certified-invoice-modal"' in html


def test_nf001j10_enables_certified_invoice_entry_without_enabling_ai():
    html = _read("web/index.html")

    certified_marker = 'id="btn-inbound-certified-invoice"'
    certified_position = html.index(certified_marker)
    certified_fragment = html[
        certified_position:certified_position + 500
    ]

    assert "Recebimento por JSON fiscal" in certified_fragment
    assert "disabled" not in certified_fragment

    ai_marker = 'id="btn-inbound-ai"'
    ai_position = html.index(ai_marker)
    ai_fragment = html[
        ai_position:ai_position + 500
    ]

    assert "LER NF POR FOTO" in ai_fragment
    assert "em desenvolvimento" in ai_fragment.lower()
    assert "disabled" in ai_fragment


def test_nf001j10_preserves_manual_receiving():
    api = _read("web/js/api.js")
    js = _read("web/js/app.js")

    assert "/api/receive" in api
    assert "registerReceive(payload)" in api
    assert "this.api.registerReceive({" in js


def test_nf001j10_uses_documentary_reconciliation_endpoint():
    api = _read("web/js/api.js")

    assert "reconcileSupplierInvoice(payload)" in api
    assert "/api/stock/onboarding" in api


def test_nf001j10_uses_j9_certified_execution_endpoint():
    api = _read("web/js/api.js")
    js = _read("web/js/app.js")

    assert "receiveCertifiedInvoice(payload)" in api
    assert "/api/invoices/receive-certified" in api
    assert "this.api.receiveCertifiedInvoice({" in js


def test_nf001j10_requires_explicit_physical_counts():
    html = _read("web/index.html")
    js = _read("web/js/app.js")

    assert "QUANTIDADE FÍSICA CONTADA" in js
    assert "certifiedConferenceCounts" in js
    assert "certified-line-count" in js
    assert "CONFERÊNCIA FÍSICA" in html


def test_nf001j10_blocks_needs_registration_lines():
    js = _read("web/js/app.js")

    assert "NEEDS_REGISTRATION" in js
    assert "RECEBIMENTO BLOQUEADO PARA ESTA LINHA" in js
    assert "isCertifiedLineBlocked" in js


def test_nf001j10_collects_traceability_for_actionable_lines():
    js = _read("web/js/app.js")

    assert "'batch_code'" in js
    assert "'expiration_date'" in js
    assert "'manufacturing_date'" in js
    assert "informe lote e validade" in js.lower()


def test_nf001j10_shows_divergence_before_execution():
    html = _read("web/index.html")
    js = _read("web/js/app.js")

    assert 'id="certified-invoice-divergence"' in html
    assert "updateCertifiedInvoiceDivergence" in js
    assert "DIVERGÊNCIA IDENTIFICADA" in html


def test_nf001j10_prevents_accidental_double_submission():
    js = _read("web/js/app.js")

    assert "this.certifiedReceivingSubmitting" in js
    assert "if (" in js
    assert "button.disabled = true" in js
    assert "RECEBIMENTO PROCESSADO" in js


def test_nf001j10_surfaces_execution_replay_and_conflict_status():
    html = _read("web/index.html")
    js = _read("web/js/app.js")

    assert 'id="certified-invoice-execution-result"' in html
    assert "executed_lines" in js
    assert "replay_lines" in js
    assert "operation_status" in js
    assert "result?.lines" in js


def test_nf001j10_javascript_has_no_direct_inventory_mutation():
    js = _read("web/js/app.js")

    certified_start = js.index(
        "resetCertifiedInvoiceReceiving()"
    )
    certified_end = js.index(
        "    bindInboundModule() {",
        certified_start,
    )

    certified = js[
        certified_start:certified_end
    ]

    assert "UPDATE inventory" not in certified
    assert "INSERT INTO" not in certified
    assert "product_repository" not in certified
    assert "SafeReceivingExecutionService" not in certified


def test_nf001j10_backend_j9_boundary_still_exists():
    backend = _read("app.py")

    assert "/api/invoices/receive-certified" in backend
    assert "OperatorReceivingIntegrationService" in backend
