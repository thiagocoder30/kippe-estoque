"""
NF-001K.3 — HTTP DANFE acquisition application boundary.

Transforms uploaded image evidence into the canonical DanfeDocument
defined by NF-001K.2.

This module deliberately contains no Flask route and has no authority
over OCR, reconciliation, product registration, receiving or stock.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any

from .danfe_acquisition import (
    DanfeAcquisitionError,
    DanfeAcquisitionMetadata,
    DanfeDocument,
)


class DanfeHttpAcquisitionError(ValueError):
    """Invalid DANFE evidence received through the HTTP boundary."""


@dataclass(frozen=True)
class DanfeHttpAcquisitionResult:
    """
    Safe HTTP-facing acquisition result.

    Original bytes remain encapsulated in the canonical DanfeDocument.
    They are intentionally not duplicated as a public result field.
    """

    document_sha256: str
    filename: str
    mime_type: str
    size_bytes: int
    source: str
    document: DanfeDocument


class DanfeHttpAcquisitionService:
    """Acquire one uploaded DANFE image as canonical document evidence."""

    SOURCE = "HTTP_UPLOAD"

    def acquire(
        self,
        *,
        uploaded_file: Any,
        operator_id: str,
        acquired_at: str,
    ) -> DanfeHttpAcquisitionResult:
        if uploaded_file is None:
            raise DanfeHttpAcquisitionError(
                "uploaded_file is required."
            )

        if not isinstance(operator_id, str) or not operator_id.strip():
            raise DanfeHttpAcquisitionError(
                "operator_id is required."
            )

        if not isinstance(acquired_at, str) or not acquired_at.strip():
            raise DanfeHttpAcquisitionError(
                "acquired_at is required."
            )

        filename = getattr(
            uploaded_file,
            "filename",
            None,
        )

        if not isinstance(filename, str) or not filename.strip():
            raise DanfeHttpAcquisitionError(
                "uploaded DANFE filename is required."
            )

        filename = filename.strip()

        mime_type = getattr(
            uploaded_file,
            "content_type",
            None,
        )

        if not isinstance(mime_type, str) or not mime_type.strip():
            raise DanfeHttpAcquisitionError(
                "uploaded DANFE MIME type is required."
            )

        mime_type = mime_type.strip().lower()

        if not mime_type.startswith("image/"):
            raise DanfeHttpAcquisitionError(
                "uploaded DANFE must be an image."
            )

        try:
            content = uploaded_file.read()
        except Exception as exc:
            raise DanfeHttpAcquisitionError(
                "unable to read uploaded DANFE."
            ) from exc

        if not isinstance(content, bytes) or not content:
            raise DanfeHttpAcquisitionError(
                "uploaded DANFE must contain image bytes."
            )

        document_sha256 = hashlib.sha256(
            content
        ).hexdigest()

        metadata = DanfeAcquisitionMetadata(
            source=self.SOURCE,
            operator_id=operator_id.strip(),
            acquired_at=acquired_at.strip(),
        )

        try:
            document = DanfeDocument(
                content=content,
                filename=filename,
                mime_type=mime_type,
                sha256=document_sha256,
                metadata=metadata,
            )
        except DanfeAcquisitionError as exc:
            raise DanfeHttpAcquisitionError(
                str(exc)
            ) from exc

        return DanfeHttpAcquisitionResult(
            document_sha256=document.sha256,
            filename=document.filename,
            mime_type=document.mime_type,
            size_bytes=len(document.content),
            source=self.SOURCE,
            document=document,
        )


__all__ = [
    "DanfeDocument",
    "DanfeHttpAcquisitionError",
    "DanfeHttpAcquisitionResult",
    "DanfeHttpAcquisitionService",
]
