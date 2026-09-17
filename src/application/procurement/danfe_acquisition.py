"""
NF-001K.2 — DANFE acquisition and extraction boundary.

This module defines value objects for the document acquisition and
extraction side of the supplier-invoice workflow.

The boundary is intentionally provider-neutral.

It has no authority to:

* mutate stock;
* execute receiving;
* persist receiving mutations;
* register products;
* reconcile products automatically.

A machine extraction remains evidence only. Human review produces the
reviewed fiscal representation that can subsequently enter the existing
invoice-preparation/reconciliation workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping


class DanfeAcquisitionError(ValueError):
    """Invalid physical DANFE evidence or acquisition metadata."""


class InvoiceExtractionError(ValueError):
    """Invalid machine-extraction evidence."""


class InvoiceReviewError(ValueError):
    """Invalid human-reviewed invoice evidence."""


def _required_text(
    value: Any,
    *,
    field_name: str,
    error_type: type[ValueError],
) -> str:
    if not isinstance(value, str):
        raise error_type(
            f"{field_name} must be a non-empty string."
        )

    normalized = value.strip()

    if not normalized:
        raise error_type(
            f"{field_name} must be a non-empty string."
        )

    return normalized


def _validate_sha256(
    value: Any,
    *,
    field_name: str,
    error_type: type[ValueError],
) -> str:
    normalized = _required_text(
        value,
        field_name=field_name,
        error_type=error_type,
    ).lower()

    if len(normalized) != 64:
        raise error_type(
            f"{field_name} must be a SHA-256 hexadecimal digest."
        )

    try:
        bytes.fromhex(normalized)
    except ValueError as exc:
        raise error_type(
            f"{field_name} must be a SHA-256 hexadecimal digest."
        ) from exc

    return normalized


@dataclass(frozen=True)
class DanfeAcquisitionMetadata:
    """
    Provenance for one captured DANFE document.

    `source` describes how the evidence entered the application, for
    example CAMERA or FILE_UPLOAD. It does not identify an OCR provider.
    """

    source: str
    operator_id: str
    acquired_at: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source",
            _required_text(
                self.source,
                field_name="source",
                error_type=DanfeAcquisitionError,
            ),
        )
        object.__setattr__(
            self,
            "operator_id",
            _required_text(
                self.operator_id,
                field_name="operator_id",
                error_type=DanfeAcquisitionError,
            ),
        )
        object.__setattr__(
            self,
            "acquired_at",
            _required_text(
                self.acquired_at,
                field_name="acquired_at",
                error_type=DanfeAcquisitionError,
            ),
        )


@dataclass(frozen=True)
class DanfeDocument:
    """
    Immutable original DANFE image evidence.

    SHA-256 binds all subsequent extraction/review evidence to the exact
    bytes acquired from the operator.
    """

    content: bytes
    filename: str
    mime_type: str
    sha256: str
    metadata: DanfeAcquisitionMetadata

    def __post_init__(self) -> None:
        if not isinstance(self.content, bytes) or not self.content:
            raise DanfeAcquisitionError(
                "DANFE content must contain image bytes."
            )

        filename = _required_text(
            self.filename,
            field_name="filename",
            error_type=DanfeAcquisitionError,
        )

        mime_type = _required_text(
            self.mime_type,
            field_name="mime_type",
            error_type=DanfeAcquisitionError,
        ).lower()

        if not mime_type.startswith("image/"):
            raise DanfeAcquisitionError(
                "DANFE evidence must use an image MIME type."
            )

        if not isinstance(
            self.metadata,
            DanfeAcquisitionMetadata,
        ):
            raise DanfeAcquisitionError(
                "metadata must be DanfeAcquisitionMetadata."
            )

        supplied_hash = _validate_sha256(
            self.sha256,
            field_name="sha256",
            error_type=DanfeAcquisitionError,
        )

        calculated_hash = hashlib.sha256(
            self.content
        ).hexdigest()

        if supplied_hash != calculated_hash:
            raise DanfeAcquisitionError(
                "DANFE SHA-256 does not match document bytes."
            )

        object.__setattr__(self, "filename", filename)
        object.__setattr__(self, "mime_type", mime_type)
        object.__setattr__(self, "sha256", supplied_hash)


@dataclass(frozen=True)
class ExtractedInvoiceField:
    """
    One machine-extracted fiscal field.

    Confidence is evidence about extraction quality, never authority to
    receive goods or mutate stock.
    """

    value: Any
    confidence: float
    requires_review: bool

    def __post_init__(self) -> None:
        if isinstance(self.confidence, bool) or not isinstance(
            self.confidence,
            (int, float),
        ):
            raise InvoiceExtractionError(
                "confidence must be numeric."
            )

        confidence = float(self.confidence)

        if confidence < 0.0 or confidence > 1.0:
            raise InvoiceExtractionError(
                "confidence must be between 0.0 and 1.0."
            )

        if not isinstance(self.requires_review, bool):
            raise InvoiceExtractionError(
                "requires_review must be boolean."
            )

        object.__setattr__(
            self,
            "confidence",
            confidence,
        )


@dataclass(frozen=True)
class ExtractedInvoiceLine:
    """
    Machine-extracted supplier-invoice line.

    Field names deliberately converge on the existing canonical invoice
    preparation contract.
    """

    supplier_product_code: ExtractedInvoiceField
    description: ExtractedInvoiceField
    gtin: ExtractedInvoiceField
    commercial_unit: ExtractedInvoiceField
    quantity: ExtractedInvoiceField
    unit_price: ExtractedInvoiceField

    def __post_init__(self) -> None:
        for field_name in (
            "supplier_product_code",
            "description",
            "gtin",
            "commercial_unit",
            "quantity",
            "unit_price",
        ):
            value = getattr(self, field_name)

            if not isinstance(
                value,
                ExtractedInvoiceField,
            ):
                raise InvoiceExtractionError(
                    f"{field_name} must be "
                    "ExtractedInvoiceField."
                )


@dataclass(frozen=True)
class InvoiceExtractionResult:
    """
    Provider-neutral result produced from one DANFE image.

    Machine extraction is explicitly non-authoritative. The
    `requires_review` state preserves the mandatory human boundary.
    """

    document_sha256: str
    invoice_number: ExtractedInvoiceField
    supplier_id: ExtractedInvoiceField
    lines: tuple[ExtractedInvoiceLine, ...]
    extractor: str
    requires_review: bool = True

    def __post_init__(self) -> None:
        document_sha256 = _validate_sha256(
            self.document_sha256,
            field_name="document_sha256",
            error_type=InvoiceExtractionError,
        )

        if not isinstance(
            self.invoice_number,
            ExtractedInvoiceField,
        ):
            raise InvoiceExtractionError(
                "invoice_number must be ExtractedInvoiceField."
            )

        if not isinstance(
            self.supplier_id,
            ExtractedInvoiceField,
        ):
            raise InvoiceExtractionError(
                "supplier_id must be ExtractedInvoiceField."
            )

        if not isinstance(self.lines, tuple):
            raise InvoiceExtractionError(
                "lines must be an immutable tuple."
            )

        if not self.lines:
            raise InvoiceExtractionError(
                "extraction must contain at least one invoice line."
            )

        if not all(
            isinstance(line, ExtractedInvoiceLine)
            for line in self.lines
        ):
            raise InvoiceExtractionError(
                "lines must contain ExtractedInvoiceLine values."
            )

        extractor = _required_text(
            self.extractor,
            field_name="extractor",
            error_type=InvoiceExtractionError,
        )

        if not isinstance(self.requires_review, bool):
            raise InvoiceExtractionError(
                "requires_review must be boolean."
            )

        object.__setattr__(
            self,
            "document_sha256",
            document_sha256,
        )
        object.__setattr__(
            self,
            "extractor",
            extractor,
        )


@dataclass(frozen=True)
class ReviewedInvoiceExtraction:
    """
    Human-reviewed fiscal representation.

    This is the output side of the acquisition/extraction boundary.
    It can represent the payload required by the existing invoice
    preparation service, but performs no reconciliation or receiving.
    """

    document_sha256: str
    invoice_number: str
    supplier_id: str
    lines: tuple[Mapping[str, Any], ...]
    reviewed_by: str
    reviewed_at: str

    def __post_init__(self) -> None:
        document_sha256 = _validate_sha256(
            self.document_sha256,
            field_name="document_sha256",
            error_type=InvoiceReviewError,
        )

        invoice_number = _required_text(
            self.invoice_number,
            field_name="invoice_number",
            error_type=InvoiceReviewError,
        )

        supplier_id = _required_text(
            self.supplier_id,
            field_name="supplier_id",
            error_type=InvoiceReviewError,
        )

        reviewed_by = _required_text(
            self.reviewed_by,
            field_name="reviewed_by",
            error_type=InvoiceReviewError,
        )

        reviewed_at = _required_text(
            self.reviewed_at,
            field_name="reviewed_at",
            error_type=InvoiceReviewError,
        )

        if not isinstance(self.lines, tuple):
            raise InvoiceReviewError(
                "lines must be an immutable tuple."
            )

        if not self.lines:
            raise InvoiceReviewError(
                "reviewed invoice must contain at least one line."
            )

        required_line_fields = {
            "supplier_product_code",
            "description",
            "gtin",
            "commercial_unit",
            "quantity",
            "unit_price",
        }

        normalized_lines: list[Mapping[str, Any]] = []

        for index, line in enumerate(self.lines):
            if not isinstance(line, Mapping):
                raise InvoiceReviewError(
                    f"line {index} must be a mapping."
                )

            missing = required_line_fields.difference(
                line.keys()
            )

            if missing:
                raise InvoiceReviewError(
                    f"line {index} is missing fields: "
                    + ", ".join(sorted(missing))
                )

            normalized_lines.append(
                dict(line)
            )

        object.__setattr__(
            self,
            "document_sha256",
            document_sha256,
        )
        object.__setattr__(
            self,
            "invoice_number",
            invoice_number,
        )
        object.__setattr__(
            self,
            "supplier_id",
            supplier_id,
        )
        object.__setattr__(
            self,
            "lines",
            tuple(normalized_lines),
        )
        object.__setattr__(
            self,
            "reviewed_by",
            reviewed_by,
        )
        object.__setattr__(
            self,
            "reviewed_at",
            reviewed_at,
        )


__all__ = [
    "DanfeAcquisitionError",
    "InvoiceExtractionError",
    "InvoiceReviewError",
    "DanfeAcquisitionMetadata",
    "DanfeDocument",
    "ExtractedInvoiceField",
    "ExtractedInvoiceLine",
    "InvoiceExtractionResult",
    "ReviewedInvoiceExtraction",
]
