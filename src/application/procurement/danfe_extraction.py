"""
NF-001K.4B — Provider-Neutral DANFE Extraction Port.

Defines the application boundary between a canonical acquired DANFE
document and any future machine-extraction implementation.

This module deliberately knows nothing about concrete OCR, multimodal
AI or cloud providers.

Architecture:

    DanfeDocument
        ->
    ExtractionRequest
        ->
    DanfeInvoiceExtractor
        ->
    InvoiceExtractionResult
        ->
    mandatory human review

Machine extraction is evidence preparation only. It has no authority
to mutate catalog, receiving, inventory or any other stock state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from src.application.procurement.danfe_acquisition import (
    DanfeDocument,
    InvoiceExtractionResult,
)


class ExtractionFailureCode(str, Enum):
    """
    Provider-neutral failure taxonomy for DANFE extraction.

    Concrete adapters may translate provider-specific failures into
    these application-level codes.
    """

    INVALID_REQUEST = "INVALID_REQUEST"
    UNSUPPORTED_DOCUMENT = "UNSUPPORTED_DOCUMENT"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    INVALID_RESULT = "INVALID_RESULT"


class ExtractionFailure(Exception):
    """
    Explicit failure raised at the machine-extraction boundary.

    Provider-specific exceptions must not leak through this
    application contract.
    """

    def __init__(
        self,
        code: ExtractionFailureCode,
        message: str,
    ) -> None:
        if not isinstance(
            code,
            ExtractionFailureCode,
        ):
            raise TypeError(
                "code must be an ExtractionFailureCode"
            )

        normalized_message = str(
            message
        ).strip()

        if not normalized_message:
            normalized_message = code.value

        self.code = code
        self.message = normalized_message

        super().__init__(
            normalized_message
        )


@dataclass(frozen=True)
class ExtractionRequest:
    """
    Canonical request presented to a DANFE extraction provider.

    The request contains only:

    * the already-acquired canonical DanfeDocument;
    * the authenticated operator identity requesting extraction.

    Provider selection, credentials, model configuration and stock
    identities belong outside this application contract.
    """

    document: DanfeDocument
    requested_by: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.document,
            DanfeDocument,
        ):
            raise ExtractionFailure(
                ExtractionFailureCode.INVALID_REQUEST,
                "document must be a canonical DanfeDocument",
            )

        if not isinstance(
            self.requested_by,
            str,
        ):
            raise ExtractionFailure(
                ExtractionFailureCode.INVALID_REQUEST,
                "requested_by must be a non-empty operator identity",
            )

        normalized_operator = (
            self.requested_by.strip()
        )

        if not normalized_operator:
            raise ExtractionFailure(
                ExtractionFailureCode.INVALID_REQUEST,
                "requested_by must be a non-empty operator identity",
            )

        object.__setattr__(
            self,
            "requested_by",
            normalized_operator,
        )


class DanfeInvoiceExtractor(ABC):
    """
    Application port implemented by machine-extraction adapters.

    Implementations may use OCR, multimodal AI, deterministic parsing,
    or another technique, but must return the canonical
    InvoiceExtractionResult.

    Implementations have no authority to:

    * approve extracted fiscal data;
    * reconcile catalog identities;
    * register products;
    * persist receiving mutations;
    * mutate inventory;
    * bypass human review.
    """

    @abstractmethod
    def extract(
        self,
        request: ExtractionRequest,
    ) -> InvoiceExtractionResult:
        """
        Extract structured invoice evidence from a canonical DANFE.

        Concrete implementations must translate provider-specific
        failures into ExtractionFailure and return an
        InvoiceExtractionResult that remains subject to human review.
        """
        raise NotImplementedError
