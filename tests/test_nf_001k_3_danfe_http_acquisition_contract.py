"""
NF-001K.3 — Real DANFE HTTP Acquisition Contract — RED.

This contract defines the HTTP/application acquisition boundary:

    authenticated multipart image
        ->
    server-side validation
        ->
    server-side SHA-256
        ->
    DanfeDocument
        ->
    acquisition response

This milestone MUST NOT:

* perform OCR;
* call an AI provider;
* reconcile invoice lines;
* register products;
* execute receiving;
* mutate stock;
* persist receiving mutations.

NF-001K.2 remains the canonical document value-object boundary.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
from io import BytesIO


MODULE_NAME = (
    "src.application.procurement."
    "danfe_http_acquisition"
)


def load_module():
    return importlib.import_module(MODULE_NAME)


def test_http_acquisition_module_exists():
    module = load_module()
    assert module is not None


def test_module_exports_required_boundary():
    module = load_module()

    required = {
        "DanfeHttpAcquisitionService",
        "DanfeHttpAcquisitionResult",
        "DanfeHttpAcquisitionError",
    }

    missing = sorted(
        name
        for name in required
        if not hasattr(module, name)
    )

    assert not missing, (
        "Missing NF-001K.3 contracts: "
        + ", ".join(missing)
    )


def test_service_accepts_uploaded_image_evidence():
    module = load_module()

    signature = inspect.signature(
        module.DanfeHttpAcquisitionService.acquire
    )

    names = set(signature.parameters)

    assert {
        "uploaded_file",
        "operator_id",
        "acquired_at",
    }.issubset(names)


def test_result_exposes_document_identity_without_image_payload():
    module = load_module()

    annotations = getattr(
        module.DanfeHttpAcquisitionResult,
        "__annotations__",
        {},
    )

    assert {
        "document_sha256",
        "filename",
        "mime_type",
        "size_bytes",
        "source",
    }.issubset(annotations)

    assert "content" not in annotations


class FakeUpload:
    def __init__(
        self,
        content: bytes,
        filename: str = "danfe.jpg",
        content_type: str = "image/jpeg",
    ):
        self.filename = filename
        self.content_type = content_type
        self.stream = BytesIO(content)

    def read(self):
        return self.stream.read()


def acquire(
    *,
    content=b"fake-image",
    filename="danfe.jpg",
    mime_type="image/jpeg",
):
    module = load_module()

    service = module.DanfeHttpAcquisitionService()

    upload = FakeUpload(
        content=content,
        filename=filename,
        content_type=mime_type,
    )

    return service.acquire(
        uploaded_file=upload,
        operator_id="operator-1",
        acquired_at="2026-09-17T18:00:00-03:00",
    )


def test_server_computes_sha256_from_received_bytes():
    content = b"real-danfe-image-evidence"

    result = acquire(content=content)

    expected = hashlib.sha256(
        content
    ).hexdigest()

    assert result.document_sha256 == expected


def test_client_cannot_supply_authoritative_sha256():
    module = load_module()

    signature = inspect.signature(
        module.DanfeHttpAcquisitionService.acquire
    )

    names = set(signature.parameters)

    assert "sha256" not in names
    assert "document_sha256" not in names


def test_acquisition_source_is_http_upload():
    result = acquire()

    assert result.source == "HTTP_UPLOAD"


def test_result_preserves_filename_and_mime():
    result = acquire(
        filename="nota-123.jpeg",
        mime_type="image/jpeg",
    )

    assert result.filename == "nota-123.jpeg"
    assert result.mime_type == "image/jpeg"


def test_result_reports_server_observed_size():
    content = b"123456789"

    result = acquire(content=content)

    assert result.size_bytes == len(content)


def test_empty_upload_is_rejected():
    module = load_module()

    try:
        acquire(content=b"")
    except module.DanfeHttpAcquisitionError:
        return

    raise AssertionError(
        "Empty DANFE upload must be rejected."
    )


def test_non_image_upload_is_rejected():
    module = load_module()

    try:
        acquire(
            content=b"not-an-image",
            filename="invoice.txt",
            mime_type="text/plain",
        )
    except module.DanfeHttpAcquisitionError:
        return

    raise AssertionError(
        "Non-image upload must be rejected."
    )


def test_missing_filename_is_rejected():
    module = load_module()

    try:
        acquire(
            filename="",
        )
    except module.DanfeHttpAcquisitionError:
        return

    raise AssertionError(
        "Upload without filename must be rejected."
    )


def test_missing_operator_identity_is_rejected():
    module = load_module()

    service = module.DanfeHttpAcquisitionService()

    upload = FakeUpload(
        content=b"image",
    )

    try:
        service.acquire(
            uploaded_file=upload,
            operator_id="",
            acquired_at="2026-09-17T18:00:00-03:00",
        )
    except module.DanfeHttpAcquisitionError:
        return

    raise AssertionError(
        "Authenticated operator identity is required."
    )


def test_service_builds_k2_danfe_document():
    module = load_module()

    result = acquire(
        content=b"k2-document",
    )

    assert isinstance(
        result.document,
        module.DanfeDocument,
    )

    assert (
        result.document.sha256
        == result.document_sha256
    )


def test_k2_document_keeps_original_bytes_inside_application_boundary():
    content = b"original-danfe-bytes"

    result = acquire(content=content)

    assert result.document.content == content


def test_http_result_does_not_expose_stock_authority():
    result = acquire()

    forbidden = (
        "receive",
        "execute_receiving",
        "mutate_stock",
        "register_product",
        "reconcile",
    )

    for name in forbidden:
        assert not hasattr(result, name)


def test_module_has_no_ocr_or_ai_provider_dependency():
    module = load_module()

    source = open(
        module.__file__,
        "r",
        encoding="utf-8",
    ).read().lower()

    forbidden = (
        "import openai",
        "from openai",
        "anthropic",
        "google.generativeai",
        "pytesseract",
        "import cv2",
        "from cv2",
    )

    for marker in forbidden:
        assert marker not in source


def test_module_does_not_import_receiving_authority():
    module = load_module()

    source = open(
        module.__file__,
        "r",
        encoding="utf-8",
    ).read()

    forbidden = (
        "receiving_execution",
        "receiving_persistence",
        "operator_receiving_integration",
        "sqlite_repository",
    )

    for marker in forbidden:
        assert marker not in source


def test_flask_route_contract_is_present_after_green():
    from pathlib import Path

    source = Path("app.py").read_text(
        encoding="utf-8",
        errors="replace",
    )

    assert "/api/invoices/danfe/acquire" in source


def test_flask_danfe_route_requires_authentication():
    import app as app_module

    app_module.app.config.update(
        TESTING=True,
    )

    client = app_module.app.test_client()

    response = client.post(
        "/api/invoices/danfe/acquire",
        data={
            "file": (
                BytesIO(b"image"),
                "danfe.jpg",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 401


def test_flask_danfe_route_requires_file(monkeypatch):
    import app as app_module

    app_module.app.config.update(
        TESTING=True,
    )

    monkeypatch.setattr(
        app_module.container.config,
        "ENV",
        "testing",
    )

    client = app_module.app.test_client()

    response = client.post(
        "/api/invoices/danfe/acquire",
        data={},
        headers={
            "X-Test-Operator-Override": "1001",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400


def test_flask_danfe_route_acquires_authenticated_image(
    monkeypatch,
):
    import app as app_module

    app_module.app.config.update(
        TESTING=True,
    )

    monkeypatch.setattr(
        app_module.container.config,
        "ENV",
        "testing",
    )

    content = b"real-http-danfe-image"

    client = app_module.app.test_client()

    response = client.post(
        "/api/invoices/danfe/acquire",
        data={
            "file": (
                BytesIO(content),
                "nota-123.jpg",
            ),
        },
        headers={
            "X-Test-Operator-Override": "1001",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201

    payload = response.get_json()

    assert payload["document_sha256"] == (
        hashlib.sha256(content).hexdigest()
    )

    assert payload["filename"] == "nota-123.jpg"
    assert payload["mime_type"] == "image/jpeg"
    assert payload["size_bytes"] == len(content)
    assert payload["source"] == "HTTP_UPLOAD"

    assert "content" not in payload
    assert "operator_id" not in payload


def test_flask_danfe_route_rejects_non_image(
    monkeypatch,
):
    import app as app_module

    app_module.app.config.update(
        TESTING=True,
    )

    monkeypatch.setattr(
        app_module.container.config,
        "ENV",
        "testing",
    )

    client = app_module.app.test_client()

    response = client.post(
        "/api/invoices/danfe/acquire",
        data={
            "file": (
                BytesIO(b"plain-text"),
                "invoice.txt",
                "text/plain",
            ),
        },
        headers={
            "X-Test-Operator-Override": "1001",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
