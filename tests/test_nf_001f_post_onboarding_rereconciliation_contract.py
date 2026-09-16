"""
NF-001F — Post-Onboarding Deterministic Re-Reconciliation.

Contract:

An invoice line that previously required product registration may be
re-evaluated after an explicit human catalog onboarding operation.

This boundary must:
- receive already-existing reconciliation evidence;
- invoke catalog reconciliation again explicitly;
- expose the new reconciliation result;
- permit NEEDS_REGISTRATION -> MATCHED after catalog creation.

It must not:
- create products;
- call onboarding;
- receive stock;
- mutate stock;
- create batches;
- perform putaway;
- infer or modify fiscal evidence.
"""

import inspect


def _subject():
    from src.application.procurement.post_onboarding_rereconciliation import (
        PostOnboardingRereconciliationService,
    )

    return PostOnboardingRereconciliationService


class ReconciliationSpy:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def reconcile(self, invoice):
        self.calls.append(invoice)
        return self.result


class Evidence:
    pass


class Result:
    pass


def test_nf001f_service_exists():
    service = _subject()

    assert inspect.isclass(service)


def test_nf001f_requires_explicit_reconciliation_authority_only():
    service = _subject()

    signature = inspect.signature(service.__init__)

    parameters = set(signature.parameters)

    assert "reconciliation_service" in parameters

    forbidden = {
        "repository",
        "product_repository",
        "stock",
        "stock_use_case",
        "receiving",
        "receiving_use_case",
        "onboarding",
        "onboarding_service",
        "existing_stock_onboarding",
        "putaway",
    }

    assert forbidden.isdisjoint(parameters)


def test_nf001f_delegates_same_invoice_evidence_to_reconciliation():
    service_type = _subject()

    invoice = Evidence()
    expected = Result()

    reconciliation = ReconciliationSpy(
        result=expected
    )

    service = service_type(
        reconciliation_service=reconciliation
    )

    result = service.execute(invoice)

    assert reconciliation.calls == [invoice]
    assert result is expected


def test_nf001f_does_not_transform_fiscal_evidence_before_reconciliation():
    service_type = _subject()

    invoice = {
        "invoice_number": "NF-001F-TEST",
        "supplier_id": "SUP-001",
        "lines": [
            {
                "description": "CAFE FISCAL CX 10X500G",
                "gtin": "7891111111111",
                "quantity": 10,
                "unit": "CX",
            }
        ],
    }

    expected = Result()

    reconciliation = ReconciliationSpy(
        result=expected
    )

    service = service_type(
        reconciliation_service=reconciliation
    )

    service.execute(invoice)

    assert reconciliation.calls[0] is invoice

    assert invoice == {
        "invoice_number": "NF-001F-TEST",
        "supplier_id": "SUP-001",
        "lines": [
            {
                "description": "CAFE FISCAL CX 10X500G",
                "gtin": "7891111111111",
                "quantity": 10,
                "unit": "CX",
            }
        ],
    }


def test_nf001f_has_no_catalog_creation_method():
    service_type = _subject()

    forbidden = {
        "register_new_product",
        "create_product",
        "onboard_product",
        "save_product",
    }

    assert forbidden.isdisjoint(
        set(dir(service_type))
    )


def test_nf001f_has_no_stock_execution_method():
    service_type = _subject()

    forbidden = {
        "receive",
        "receive_stock",
        "add_stock",
        "putaway",
        "create_batch",
    }

    assert forbidden.isdisjoint(
        set(dir(service_type))
    )
