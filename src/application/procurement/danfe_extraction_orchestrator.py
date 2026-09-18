"""
NF-001K.4C — Structured DANFE Extraction Orchestrator.

Application-level orchestration for provider-neutral machine extraction
of one canonical DANFE document.

The orchestrator has authority only to:

* validate the canonical extraction request;
* invoke exactly one configured DanfeInvoiceExtractor;
* normalize unexpected extractor failures;
* validate the contextual integrity of the extraction result;
* preserve the mandatory human-review boundary.

Machine extraction remains evidence only.

This module has no authority to approve fiscal data, reconcile catalog
identities, register products, execute receiving, persist receiving
mutations or mutate inventory.
"""

from __future__ import annotations

from src.application.procurement.danfe_acquisition import (
    InvoiceExtractionResult,
)
from src.application.procurement.danfe_extraction import (
    DanfeInvoiceExtractor,
    ExtractionFailure,
    ExtractionFailureCode,
    ExtractionRequest,
)


class DanfeExtractionOrchestrator:
    """
    Execute one canonical DANFE machine-extraction operation.

    The configured extractor is an application port implementation.
    Concrete provider configuration belongs outside this orchestrator.

    A successful machine result is still non-authoritative and must
    remain explicitly subject to human review.
    """

    def __init__(
        self,
        extractor: DanfeInvoiceExtractor,
    ) -> None:
        if not isinstance(
            extractor,
            DanfeInvoiceExtractor,
        ):
            raise ExtractionFailure(
                ExtractionFailureCode.INVALID_REQUEST,
                "extractor must implement DanfeInvoiceExtractor",
            )

        self._extractor = extractor

    def extract(
        self,
        request: ExtractionRequest,
    ) -> InvoiceExtractionResult:
        """
        Execute and validate one structured extraction.

        Explicit application-boundary ExtractionFailure values are
        preserved unchanged. Unexpected implementation failures are
        translated into the provider-neutral EXTRACTION_FAILED code.
        """

        if not isinstance(
            request,
            ExtractionRequest,
        ):
            raise ExtractionFailure(
                ExtractionFailureCode.INVALID_REQUEST,
                "request must be a canonical ExtractionRequest",
            )

        try:
            result = self._extractor.extract(
                request
            )
        except ExtractionFailure:
            raise
        except Exception as exc:
            raise ExtractionFailure(
                ExtractionFailureCode.EXTRACTION_FAILED,
                "machine extraction failed",
            ) from exc

        if not isinstance(
            result,
            InvoiceExtractionResult,
        ):
            raise ExtractionFailure(
                ExtractionFailureCode.INVALID_RESULT,
                "extractor returned a non-canonical result",
            )

        if (
            result.document_sha256
            != request.document.sha256
        ):
            raise ExtractionFailure(
                ExtractionFailureCode.INVALID_RESULT,
                "extraction result does not match DANFE identity",
            )

        if result.requires_review is not True:
            raise ExtractionFailure(
                ExtractionFailureCode.INVALID_RESULT,
                "machine extraction must require human review",
            )

        return result


__all__ = [
    "DanfeExtractionOrchestrator",
]
