"""
NF-001K.5A-D — Mandatory Fiscal Classification RED contract.

Security objective
------------------

A DANFE/fiscal-document outbound operation must never rely on the
caller to choose its data classification.

Fiscal egress metadata must be constructed through a dedicated
boundary that assigns SENSITIVE_FISCAL by construction.

This contract does NOT:

* perform network requests;
* transmit document bytes;
* contain credentials;
* authorize any provider;
* create an ALLOW rule;
* change receiving or stock.
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect

import pytest


MODULE_NAME = (
    "src.infrastructure.security.data_egress"
)


def load_module():
    return importlib.import_module(MODULE_NAME)


def make_fiscal_request(
    module,
    *,
    destination="external-document-service",
    requested_by="nf-001k.5a-d-test",
):
    return module.create_fiscal_document_egress_request(
        destination=destination,
        requested_by=requested_by,
    )


def test_fiscal_egress_factory_exists():
    module = load_module()

    assert hasattr(
        module,
        "create_fiscal_document_egress_request",
    )

    assert callable(
        module.create_fiscal_document_egress_request
    )


def test_fiscal_factory_returns_canonical_egress_request():
    module = load_module()

    request = make_fiscal_request(module)

    assert isinstance(
        request,
        module.EgressRequest,
    )


def test_fiscal_factory_forces_sensitive_fiscal_classification():
    module = load_module()

    request = make_fiscal_request(module)

    assert (
        request.classification
        is module.EgressDataClassification.SENSITIVE_FISCAL
    )


def test_fiscal_factory_forces_document_extraction_purpose():
    module = load_module()

    request = make_fiscal_request(module)

    assert (
        request.purpose
        is module.EgressPurpose.DOCUMENT_EXTRACTION
    )


def test_fiscal_factory_preserves_destination_metadata():
    module = load_module()

    request = make_fiscal_request(
        module,
        destination="provider-under-evaluation",
    )

    assert (
        request.destination
        == "provider-under-evaluation"
    )


def test_fiscal_factory_preserves_requester_metadata():
    module = load_module()

    request = make_fiscal_request(
        module,
        requested_by="danfe-extraction-adapter",
    )

    assert (
        request.requested_by
        == "danfe-extraction-adapter"
    )


def test_fiscal_factory_does_not_accept_classification_override():
    module = load_module()

    with pytest.raises(TypeError):
        module.create_fiscal_document_egress_request(
            destination="external-provider",
            requested_by="attacker-test",
            classification=(
                module.EgressDataClassification.PUBLIC
            ),
        )


def test_fiscal_factory_does_not_accept_purpose_override():
    module = load_module()

    with pytest.raises(TypeError):
        module.create_fiscal_document_egress_request(
            destination="external-provider",
            requested_by="attacker-test",
            purpose=(
                module.EgressPurpose.DOCUMENT_EXTRACTION
            ),
        )


@pytest.mark.parametrize(
    "classification_name",
    (
        "PUBLIC",
        "INTERNAL",
        "CONFIDENTIAL",
        "SECRET",
    ),
)
def test_fiscal_classification_cannot_be_downgraded_by_caller(
    classification_name,
):
    module = load_module()

    classification = getattr(
        module.EgressDataClassification,
        classification_name,
    )

    with pytest.raises(TypeError):
        module.create_fiscal_document_egress_request(
            destination="external-provider",
            requested_by="downgrade-attempt",
            classification=classification,
        )


def test_fiscal_request_remains_immutable():
    module = load_module()

    request = make_fiscal_request(module)

    with pytest.raises(
        dataclasses.FrozenInstanceError
    ):
        request.classification = (
            module.EgressDataClassification.PUBLIC
        )


def test_fiscal_request_is_denied_by_current_policy():
    module = load_module()

    policy = module.SecureDataEgressPolicy()
    request = make_fiscal_request(module)

    assert (
        policy.evaluate(request)
        is module.EgressDecision.DENY
    )


def test_fiscal_factory_has_no_payload_parameter():
    module = load_module()

    signature = inspect.signature(
        module.create_fiscal_document_egress_request
    )

    names = {
        name.lower()
        for name in signature.parameters
    }

    forbidden = {
        "payload",
        "content",
        "bytes",
        "document",
        "danfe",
        "image",
        "invoice",
        "api_key",
        "token",
        "secret",
        "password",
    }

    assert not names.intersection(
        forbidden
    )


def test_fiscal_factory_source_has_no_network_behavior():
    module = load_module()

    source = inspect.getsource(
        module.create_fiscal_document_egress_request
    ).lower()

    forbidden = (
        "requests.",
        "httpx.",
        "urlopen",
        "socket.",
        "aiohttp",
        "openai",
        "anthropic",
        "gemini",
        "groq",
        "fetch(",
    )

    for token in forbidden:
        assert token not in source


def test_fiscal_factory_source_has_no_receiving_or_stock_authority():
    module = load_module()

    source = inspect.getsource(
        module.create_fiscal_document_egress_request
    ).lower()

    forbidden = (
        "receiving_execution",
        "receiving_persistence",
        "operator_receiving",
        "sqlite_repository",
        "stock_repository",
        "inventory_repository",
        "register_product",
        "mutate_stock",
    )

    for token in forbidden:
        assert token not in source


def test_fiscal_factory_is_public_security_contract():
    module = load_module()

    assert (
        "create_fiscal_document_egress_request"
        in module.__all__
    )
