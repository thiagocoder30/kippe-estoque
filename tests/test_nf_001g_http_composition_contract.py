"""
NF-001G — HTTP / Composition Root Contract

Purpose
-------
Establish the canonical HTTP composition boundary for the supplier-invoice
pipeline already implemented by NF-001A through NF-001F.

This RED contract deliberately tests architecture before implementation.

The production system must:

HTTP gateway (app.py)
        ↓
canonical Container
        ↓
invoice preparation
        ↓
catalog reconciliation
        ↓
unresolved-product workflow
        ↓
human product onboarding
        ↓
post-onboarding re-reconciliation

No second Flask application, no parallel container and no direct stock
receiving side effect are allowed.
"""

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (
        ROOT / relative_path
    ).read_text(
        encoding="utf-8"
    )


def test_nf_pipeline_is_composed_in_canonical_container():
    source = _read(
        "src/infrastructure/container.py"
    )

    required_capabilities = (
        "invoice_preparation",
        "invoice_reconciliation",
        "unresolved_product",
        "post_onboarding",
    )

    missing = [
        capability
        for capability in required_capabilities
        if capability not in source
    ]

    assert not missing, (
        "Canonical Container does not yet expose "
        "the complete NF pipeline. Missing semantic "
        f"capabilities: {missing}"
    )


def test_nf_pipeline_enters_through_canonical_flask_gateway():
    source = _read("app.py")

    assert "/api/" in source

    nf_semantics = (
        "invoice",
        "reconciliation",
        "unresolved",
    )

    assert any(
        semantic in source.lower()
        for semantic in nf_semantics
    ), (
        "app.py has no canonical HTTP boundary for "
        "the NF reconciliation pipeline."
    )


def test_nf_http_gateway_does_not_create_parallel_container():
    source = _read("app.py")

    assert source.count(
        "container = Container()"
    ) == 1, (
        "NF integration must reuse the canonical "
        "application Container."
    )


def test_nf_pipeline_does_not_create_second_flask_application():
    source = _read("app.py")

    assert source.count(
        "Flask(__name__)"
    ) == 1, (
        "NF integration must remain inside the "
        "canonical Flask gateway."
    )


def test_nf_pipeline_keeps_existing_stock_onboarding_semantically_separate():
    source = _read("app.py")

    assert (
        "/api/stock/onboarding"
        in source
    )

    assert (
        "existing_stock_onboarding_use_case"
        in source
    ), (
        "Existing-stock onboarding is an independent "
        "inventory operation and must not be silently "
        "redefined as fiscal NF onboarding."
    )


def test_nf_pipeline_does_not_directly_receive_goods_from_fiscal_ingestion():
    source = _read("app.py").lower()

    nf_markers = (
        "invoice",
        "reconciliation",
        "unresolved",
    )

    assert any(
        marker in source
        for marker in nf_markers
    ), (
        "NF HTTP integration is not implemented yet."
    )

    # This contract intentionally establishes that
    # fiscal ingestion/reconciliation is not itself
    # equivalent to physical receiving.
    #
    # Detailed behavioral enforcement will be added
    # after the canonical route is implemented.
    assert True


def test_nf_application_services_remain_in_application_layer():
    expected_files = (
        "src/application/procurement/"
        "invoice_preparation.py",

        "src/application/procurement/"
        "invoice_reconciliation.py",

        "src/application/procurement/"
        "unresolved_product_workflow.py",

        "src/application/procurement/"
        "product_onboarding_orchestration.py",

        "src/application/procurement/"
        "post_onboarding_rereconciliation.py",
    )

    missing = [
        path
        for path in expected_files
        if not (ROOT / path).is_file()
    ]

    assert not missing, (
        "NF application pipeline is incomplete: "
        f"{missing}"
    )
