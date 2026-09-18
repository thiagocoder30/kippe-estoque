"""
Kippe — Secure Data Egress Authority.

This module defines the security decision boundary for data attempting
to leave the Kippe local trust perimeter.

Security posture
----------------

FAIL CLOSED.

The absence of an explicitly certified outbound policy is always DENY.

This authority intentionally contains:

* no network implementation;
* no provider SDK;
* no credentials;
* no document bytes;
* no fiscal payload;
* no persistence authority;
* no receiving authority;
* no stock authority.

An EgressRequest contains only the minimum security metadata necessary
to evaluate whether an outbound operation may be considered.

Fiscal document egress must be constructed through
create_fiscal_document_egress_request(). That boundary assigns
SENSITIVE_FISCAL and DOCUMENT_EXTRACTION by construction. The caller
cannot supply or downgrade either value.

This milestone intentionally provides no ALLOW rule. A future policy
may grant outbound authority only through an explicit, independently
certified security contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EgressDecision(Enum):
    """Explicit outbound-data security decision."""

    ALLOW = "allow"
    DENY = "deny"


class EgressDataClassification(Enum):
    """Security classification applied before any outbound decision."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SENSITIVE_FISCAL = "sensitive_fiscal"
    SECRET = "secret"


class EgressPurpose(Enum):
    """Declared reason for the requested outbound operation."""

    DOCUMENT_EXTRACTION = "document_extraction"


@dataclass(frozen=True)
class EgressRequest:
    """
    Security metadata for one proposed outbound operation.

    The actual business payload must never be placed inside this object.

    This separation is intentional: the security authority decides
    whether an operation is authorized without acquiring custody of
    DANFE bytes, fiscal records, credentials or provider secrets.
    """

    classification: EgressDataClassification
    purpose: EgressPurpose
    destination: str
    requested_by: str


def create_fiscal_document_egress_request(
    *,
    destination: str,
    requested_by: str,
) -> EgressRequest:
    """
    Construct canonical security metadata for fiscal-document egress.

    Classification and purpose are intentionally not parameters.

    A caller preparing DANFE/fiscal-document egress therefore cannot
    downgrade SENSITIVE_FISCAL or redefine DOCUMENT_EXTRACTION through
    this boundary.

    This function does not receive document content, perform network
    I/O, access credentials, authorize a provider, persist data, mutate
    stock or execute receiving.
    """

    return EgressRequest(
        classification=(
            EgressDataClassification.SENSITIVE_FISCAL
        ),
        purpose=(
            EgressPurpose.DOCUMENT_EXTRACTION
        ),
        destination=destination,
        requested_by=requested_by,
    )


class SecureDataEgressPolicy:
    """
    Fail-closed outbound-data policy.

    No destination is currently certified.

    Therefore every request is denied.

    Future ALLOW behavior must be introduced by an explicit security
    milestone and corresponding contract rather than by weakening this
    default implementation.
    """

    def evaluate(
        self,
        request: EgressRequest,
    ) -> EgressDecision:
        if not isinstance(
            request,
            EgressRequest,
        ):
            return EgressDecision.DENY

        return EgressDecision.DENY


__all__ = [
    "EgressDecision",
    "EgressDataClassification",
    "EgressPurpose",
    "EgressRequest",
    "create_fiscal_document_egress_request",
    "SecureDataEgressPolicy",
]
