"""
NF-001K.5A-B — Secure Data Egress Authority RED contract.

Purpose
-------

Introduce a single fail-closed application/security authority governing
whether Kippe data may leave the local trust boundary.

This milestone does NOT:

* integrate an OCR or AI provider;
* perform network requests;
* introduce provider credentials;
* transmit DANFE bytes;
* change receiving;
* change stock;
* weaken mandatory human review.

The future authority must default to DENY and must require explicit,
structured authorization before an outbound-data adapter can be used.
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
from pathlib import Path

import pytest


MODULE_NAME = (
    "src.infrastructure.security.data_egress"
)


def load_module():
    return importlib.import_module(MODULE_NAME)


def test_secure_data_egress_module_exists():
    module = load_module()
    assert module is not None


def test_egress_decision_is_explicit_enum():
    module = load_module()

    assert hasattr(module, "EgressDecision")

    decision = module.EgressDecision

    assert hasattr(decision, "ALLOW")
    assert hasattr(decision, "DENY")

    assert decision.ALLOW != decision.DENY


def test_egress_data_classification_is_explicit():
    module = load_module()

    assert hasattr(module, "EgressDataClassification")

    classification = module.EgressDataClassification

    required = (
        "PUBLIC",
        "INTERNAL",
        "CONFIDENTIAL",
        "SENSITIVE_FISCAL",
        "SECRET",
    )

    for name in required:
        assert hasattr(classification, name)


def test_egress_purpose_is_explicit():
    module = load_module()

    assert hasattr(module, "EgressPurpose")

    purpose = module.EgressPurpose

    assert hasattr(
        purpose,
        "DOCUMENT_EXTRACTION",
    )


def test_egress_request_is_immutable():
    module = load_module()

    assert hasattr(module, "EgressRequest")

    cls = module.EgressRequest

    assert dataclasses.is_dataclass(cls)

    params = getattr(
        cls,
        "__dataclass_params__",
        None,
    )

    assert params is not None
    assert params.frozen is True


def test_egress_request_contains_security_context_only():
    module = load_module()

    cls = module.EgressRequest

    field_names = {
        field.name
        for field in dataclasses.fields(cls)
    }

    required = {
        "classification",
        "purpose",
        "destination",
        "requested_by",
    }

    assert required.issubset(field_names)

    forbidden = {
        "content",
        "bytes",
        "payload",
        "document",
        "image",
        "api_key",
        "token",
        "secret",
        "password",
    }

    assert not field_names.intersection(
        forbidden
    )


def test_policy_defaults_to_deny():
    module = load_module()

    policy = module.SecureDataEgressPolicy()

    request = module.EgressRequest(
        classification=(
            module.EgressDataClassification.PUBLIC
        ),
        purpose=(
            module.EgressPurpose.DOCUMENT_EXTRACTION
        ),
        destination="unconfigured-provider",
        requested_by="operator-test",
    )

    decision = policy.evaluate(request)

    assert decision == module.EgressDecision.DENY


@pytest.mark.parametrize(
    "classification_name",
    (
        "INTERNAL",
        "CONFIDENTIAL",
        "SENSITIVE_FISCAL",
        "SECRET",
    ),
)
def test_non_public_data_is_denied_without_explicit_policy(
    classification_name,
):
    module = load_module()

    policy = module.SecureDataEgressPolicy()

    classification = getattr(
        module.EgressDataClassification,
        classification_name,
    )

    request = module.EgressRequest(
        classification=classification,
        purpose=(
            module.EgressPurpose.DOCUMENT_EXTRACTION
        ),
        destination="external-provider",
        requested_by="operator-test",
    )

    assert (
        policy.evaluate(request)
        == module.EgressDecision.DENY
    )


def test_sensitive_fiscal_data_is_fail_closed():
    module = load_module()

    policy = module.SecureDataEgressPolicy()

    request = module.EgressRequest(
        classification=(
            module.EgressDataClassification
            .SENSITIVE_FISCAL
        ),
        purpose=(
            module.EgressPurpose.DOCUMENT_EXTRACTION
        ),
        destination="external-ai",
        requested_by="operator-test",
    )

    assert (
        policy.evaluate(request)
        == module.EgressDecision.DENY
    )


def test_policy_never_receives_actual_document_payload():
    module = load_module()

    source = inspect.getsource(
        module.EgressRequest
    ).lower()

    forbidden = (
        "danfedocument",
        "invoiceextractionresult",
        "content: bytes",
        "api_key",
        "authorization",
    )

    for token in forbidden:
        assert token not in source


def test_security_module_has_no_network_dependency():
    module = load_module()

    source = inspect.getsource(module).lower()

    forbidden = (
        "import requests",
        "from requests",
        "import httpx",
        "from httpx",
        "urllib.request",
        "aiohttp",
        "socket.",
        "openai",
        "anthropic",
        "google.cloud",
        "gemini",
    )

    for token in forbidden:
        assert token not in source


def test_security_authority_has_no_stock_authority():
    module = load_module()

    source = inspect.getsource(module).lower()

    forbidden = (
        "sqlite_repository",
        "receive_goods",
        "receiving_execution",
        "operator_receiving",
        "inventory_repository",
        "stock_repository",
    )

    for token in forbidden:
        assert token not in source


def test_existing_extraction_port_remains_provider_neutral():
    source = Path(
        "src/application/procurement/"
        "danfe_extraction.py"
    ).read_text(
        encoding="utf-8"
    ).lower()

    forbidden = (
        "import openai",
        "from openai",
        "import anthropic",
        "from anthropic",
        "google.cloud",
        "api_key",
    )

    for token in forbidden:
        assert token not in source


def test_existing_orchestrator_remains_provider_neutral():
    source = Path(
        "src/application/procurement/"
        "danfe_extraction_orchestrator.py"
    ).read_text(
        encoding="utf-8"
    ).lower()

    forbidden = (
        "import openai",
        "from openai",
        "import anthropic",
        "from anthropic",
        "google.cloud",
        "api_key",
    )

    for token in forbidden:
        assert token not in source


def test_human_review_boundary_remains_mandatory():
    source = Path(
        "src/application/procurement/"
        "danfe_extraction_orchestrator.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "result.requires_review is not True"
        in source
    )


def test_security_contract_does_not_modify_receiving():
    module = load_module()

    source = inspect.getsource(module).lower()

    forbidden = (
        "execute_receiving",
        "receive_certified",
        "persist_receiving",
        "mutate_stock",
        "register_product",
    )

    for token in forbidden:
        assert token not in source
