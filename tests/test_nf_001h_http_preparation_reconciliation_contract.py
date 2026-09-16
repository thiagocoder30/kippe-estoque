"""
NF-001H — HTTP Preparation + Catalog Reconciliation Contract

Purpose
-------
Establish the first behavioral HTTP boundary for supplier-invoice processing.

The endpoint receives already-extracted fiscal data.

Extraction itself remains outside this slice. The payload may eventually
originate from OCR, XML or explicit manual entry, but all ingestion mechanisms
must converge on the same neutral NF preparation contract.

Required flow:

HTTP
    -> canonical Container
    -> InvoicePreparationService
    -> CatalogReconciliationService
    -> UnresolvedProductWorkflowService
    -> JSON documentary/reconciliation result

This endpoint MUST NOT:
- receive stock;
- mutate quantities;
- perform putaway;
- automatically create products;
- infer missing catalog master data.
"""

import importlib

import pytest


@pytest.fixture
def application_module(monkeypatch, tmp_path):
    """
    Import the canonical Flask gateway with an isolated database whenever the
    current Config contract supports environment-level DB isolation.

    The application itself remains the canonical app.py.
    """

    monkeypatch.setenv(
        "KIPPE_ENV",
        "testing",
    )
    monkeypatch.setenv(
        "KIPPE_DB_PATH",
        str(tmp_path / "nf001h.db"),
    )
    monkeypatch.setenv(
        "KIPPE_LOG_PATH",
        str(tmp_path / "nf001h.log"),
    )

    module = importlib.import_module("app")

    module.app.config.update(
        TESTING=True,
    )

    return module


@pytest.fixture
def client(application_module):
    return application_module.app.test_client()


def _payload():
    return {
        "invoice_number": "000123456",
        "supplier_id": "SUP-001",
        "access_key": "1" * 44,
        "series": "1",
        "origin_document": "OCR",
        "lines": [
            {
                "supplier_product_code": "FORN-7788",
                "description": "CAFE TORRADO 500G",
                "gtin": "7899999999999",
                "commercial_unit": "UN",
                "quantity": 12,
                "unit_price": 9.90,
            }
        ],
    }


def test_nf_http_endpoint_exists(client):
    response = client.post(
        "/api/invoices/reconcile",
        json=_payload(),
    )

    assert response.status_code != 404


def test_nf_http_endpoint_accepts_structured_fiscal_payload(client):
    response = client.post(
        "/api/invoices/reconcile",
        json=_payload(),
    )

    assert response.status_code == 200

    body = response.get_json()

    assert isinstance(body, dict)


def test_nf_http_response_preserves_document_identity(client):
    response = client.post(
        "/api/invoices/reconcile",
        json=_payload(),
    )

    assert response.status_code == 200

    body = response.get_json()

    assert body["invoice_number"] == "000123456"
    assert body["supplier_id"] == "SUP-001"
    assert body["access_key"] == "1" * 44
    assert body["series"] == "1"
    assert body["origin_document"] == "OCR"


def test_unknown_gtin_is_returned_as_explicit_pending_catalog_action(client):
    response = client.post(
        "/api/invoices/reconcile",
        json=_payload(),
    )

    assert response.status_code == 200

    body = response.get_json()

    assert body["total_lines"] == 1
    assert body["matched_lines"] == 0
    assert body["needs_registration_lines"] == 1
    assert body["is_fully_reconciled"] is False

    assert len(body["pending_products"]) == 1

    pending = body["pending_products"][0]

    assert pending["supplier_product_code"] == "FORN-7788"
    assert pending["description"] == "CAFE TORRADO 500G"
    assert pending["gtin"] == "7899999999999"
    assert pending["commercial_unit"] == "UN"
    assert pending["quantity"] == 12
    assert pending["reason"] == "UNKNOWN_GTIN"


def test_nf_http_rejects_missing_json_body(client):
    response = client.post(
        "/api/invoices/reconcile",
        content_type="application/json",
    )

    assert response.status_code == 400


def test_nf_http_rejects_invalid_fiscal_quantity(client):
    payload = _payload()
    payload["lines"][0]["quantity"] = 0

    response = client.post(
        "/api/invoices/reconcile",
        json=payload,
    )

    assert response.status_code == 400


def test_nf_http_does_not_automatically_create_unknown_product(
    client,
    application_module,
):
    repository = application_module.container.product_repository

    ean = "7899999999999"

    assert repository.get_by_ean(ean) is None

    response = client.post(
        "/api/invoices/reconcile",
        json=_payload(),
    )

    assert response.status_code == 200
    assert repository.get_by_ean(ean) is None


def test_nf_http_does_not_call_physical_receiving(
    client,
    application_module,
):
    class ForbiddenReceiving:
        def execute(self, *args, **kwargs):
            raise AssertionError(
                "NF documentary reconciliation must not receive stock"
            )

    application_module.container._receiving_use_case = ForbiddenReceiving()

    response = client.post(
        "/api/invoices/reconcile",
        json=_payload(),
    )

    assert response.status_code == 200


def test_nf_http_does_not_call_existing_stock_onboarding(
    client,
    application_module,
):
    class ForbiddenOnboarding:
        def execute(self, *args, **kwargs):
            raise AssertionError(
                "NF reconciliation must not invoke stock onboarding"
            )

    application_module.container._existing_stock_onboarding_use_case = (
        ForbiddenOnboarding()
    )

    response = client.post(
        "/api/invoices/reconcile",
        json=_payload(),
    )

    assert response.status_code == 200
