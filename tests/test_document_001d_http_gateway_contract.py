"""
DOCUMENT-001D
HTTP gateway contract for invoice/document attachments.

This slice defines only the HTTP boundary over the already
certified DOCUMENT-001A/B/C capabilities.

No frontend contract belongs here.
"""

from io import BytesIO
from pathlib import Path

import pytest


PDF_BYTES = (
    b"%PDF-1.7\n"
    b"KIPPE DOCUMENT-001D TEST\n"
    b"%%EOF\n"
)


ATTACHMENT_ID = "DOC-HTTP-001"

METADATA_ROUTE = (
    f"/api/document-attachments/{ATTACHMENT_ID}"
)

CONTENT_ROUTE = (
    f"/api/document-attachments/{ATTACHMENT_ID}/content"
)


@pytest.fixture()
def app_module(tmp_path, monkeypatch):
    import app as module

    module.app.config.update(
        TESTING=True,
    )

    test_db = (
        tmp_path
        / "document-001d-http.db"
    )

    document_root = (
        tmp_path
        / "documents"
    )

    monkeypatch.setattr(
        module.container.config,
        "ENV",
        "testing",
    )

    monkeypatch.setattr(
        module.container.config,
        "DB_PATH",
        str(test_db),
    )

    monkeypatch.setattr(
        module.container.config,
        "DOCUMENT_ROOT",
        str(document_root),
    )

    module.container._product_repository = None
    module.container._document_storage = None
    module.container._document_attachment_use_case = None

    repository = (
        module.container.product_repository
    )

    event_id = (
        repository
        .append_operational_audit_event(
            event_type="RECEBIMENTO",
            product_id="SKU-DOCUMENT-001D",
            batch_code="L-DOCUMENT-001D",
            supplier="FORNECEDOR TESTE",
            document_id="NF-77",
            origin_document="MANUAL",
            operator_id="1001",
            metadata={
                "test": "DOCUMENT-001D",
            },
        )
    )

    module._document_001d_test_event_id = (
        event_id
    )

    stored = (
        module
        .container
        .document_storage
        .store(
            content=PDF_BYTES,
            original_filename=(
                "document-http-001.pdf"
            ),
            declared_mime_type=(
                "application/pdf"
            ),
        )
    )

    repository.create_and_link_document_attachment(
        event_id=event_id,
        attachment_id=ATTACHMENT_ID,
        business_document_number="NF-HTTP-001",
        supplier="FORNECEDOR TESTE",
        original_filename=stored[
            "original_filename"
        ],
        stored_filename=stored[
            "stored_filename"
        ],
        relative_path=stored[
            "relative_path"
        ],
        mime_type=stored[
            "mime_type"
        ],
        byte_size=stored[
            "byte_size"
        ],
        sha256=stored[
            "sha256"
        ],
        operator_id="1001",
    )

    return module


@pytest.fixture()
def upload_route(app_module):
    return (
        "/api/audit-events/"
        f"{app_module._document_001d_test_event_id}"
        "/attachments"
    )


@pytest.fixture()
def client(app_module):
    return app_module.app.test_client()


def authenticated_headers():
    """
    Existing infrastructure explicitly provides testing-only
    operator/role overrides.

    Tests use the existing identity boundary instead of adding
    a new authentication mechanism for DOCUMENT-001D.
    """
    return {
        "X-Test-Operator-Override": "1001",
        "X-Test-Role-Override": "ADMIN",
    }


def upload_payload(**extra):
    payload = {
        "file": (
            BytesIO(PDF_BYTES),
            "nota-fiscal.pdf",
        ),
        "business_document_number": "NF-77",
        "supplier": "FORNECEDOR TESTE",
    }

    payload.update(extra)

    return payload


def test_upload_route_exists_and_does_not_return_404(
    client,
    upload_route,
):
    response = client.post(
        upload_route,
        data=upload_payload(),
        headers=authenticated_headers(),
        content_type="multipart/form-data",
    )

    assert response.status_code != 404


def test_upload_requires_authenticated_operator(
    client,
    upload_route,
):
    response = client.post(
        upload_route,
        data=upload_payload(),
        content_type="multipart/form-data",
    )

    assert response.status_code in (
        401,
        403,
    )


def test_upload_accepts_multipart_document(
    client,
    upload_route,
):
    response = client.post(
        upload_route,
        data=upload_payload(),
        headers=authenticated_headers(),
        content_type="multipart/form-data",
    )

    assert response.status_code in (
        200,
        201,
    )


def test_upload_rejects_request_without_file(
    client,
    upload_route,
):
    response = client.post(
        upload_route,
        data={
            "business_document_number": "NF-77",
            "supplier": "FORNECEDOR TESTE",
        },
        headers=authenticated_headers(),
        content_type="multipart/form-data",
    )

    assert response.status_code == 400


def test_upload_does_not_trust_client_operator_id(
    client,
    monkeypatch,
    app_module,
    upload_route,
):
    captured = {}

    class FakeUseCase:
        def attach(self, **kwargs):
            captured.update(kwargs)

            return {
                "attachment_id": "DOC-HTTP-001",
                "original_filename": "nota-fiscal.pdf",
                "stored_filename": "DOC-HTTP-001.pdf",
                "relative_path": "2026/09/DOC-HTTP-001.pdf",
                "mime_type": "application/pdf",
                "byte_size": len(PDF_BYTES),
                "sha256": "a" * 64,
            }

    candidate_names = (
        "document_attachment_use_case",
        "attach_document_use_case",
        "document_use_case",
    )

    patched = False

    for name in candidate_names:
        if hasattr(
            app_module.container,
            name,
        ):
            monkeypatch.setattr(
                app_module.container,
                name,
                FakeUseCase(),
            )
            patched = True
            break

    if not patched:
        pytest.fail(
            "DOCUMENT-001D composition authority "
            "is not exposed by Container yet."
        )

    response = client.post(
        upload_route,
        data=upload_payload(
            operator_id="ATTACKER",
        ),
        headers=authenticated_headers(),
        content_type="multipart/form-data",
    )

    assert response.status_code in (
        200,
        201,
    )

    assert captured["operator_id"] == "1001"
    assert captured["operator_id"] != "ATTACKER"


def test_upload_delegates_to_document_attachment_use_case():
    source = Path(
        "app.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "AttachDocumentToAuditEventUseCase"
        in source
        or "document_attachment_use_case"
        in source
        or "attach_document_use_case"
        in source
    )


def test_metadata_route_exists_for_authenticated_operator(
    client,
):
    response = client.get(
        METADATA_ROUTE,
        headers=authenticated_headers(),
    )

    assert response.status_code != 404


def test_metadata_route_requires_authentication(
    client,
):
    response = client.get(
        METADATA_ROUTE,
    )

    assert response.status_code in (
        401,
        403,
    )


def test_missing_attachment_returns_404(
    client,
):
    response = client.get(
        "/api/document-attachments/"
        "DOES-NOT-EXIST",
        headers=authenticated_headers(),
    )

    assert response.status_code == 404


def test_content_route_exists_for_authenticated_operator(
    client,
):
    response = client.get(
        CONTENT_ROUTE,
        headers=authenticated_headers(),
    )

    assert response.status_code != 404


def test_content_route_requires_authentication(
    client,
):
    response = client.get(
        CONTENT_ROUTE,
    )

    assert response.status_code in (
        401,
        403,
    )


def test_missing_attachment_content_returns_404(
    client,
):
    response = client.get(
        "/api/document-attachments/"
        "DOES-NOT-EXIST/content",
        headers=authenticated_headers(),
    )

    assert response.status_code == 404


def test_http_gateway_does_not_accept_relative_path_from_client():
    source = Path(
        "app.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden = (
        'request.form.get("relative_path")',
        "request.form.get('relative_path')",
        'request.args.get("relative_path")',
        "request.args.get('relative_path')",
    )

    for marker in forbidden:
        assert marker not in source


def test_http_gateway_does_not_accept_stored_filename_from_client():
    source = Path(
        "app.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden = (
        'request.form.get("stored_filename")',
        "request.form.get('stored_filename')",
        'request.args.get("stored_filename")',
        "request.args.get('stored_filename')",
    )

    for marker in forbidden:
        assert marker not in source


def test_http_gateway_does_not_create_product_or_batch_authority():
    source = Path(
        "app.py"
    ).read_text(
        encoding="utf-8"
    )

    marker = (
        "/api/audit-events/<int:event_id>/attachments"
    )

    assert marker in source

    start = source.index(marker)

    section_marker = (
        "# DOCUMENT-001D — DOCUMENT ATTACHMENT HTTP GATEWAY"
    )

    section_start = source.rfind(
        section_marker,
        0,
        start,
    )

    assert section_start >= 0

    region = source[
        section_start:
        start + 12000
    ]

    forbidden = (
        "Product(",
        "Batch(",
        "save_product(",
        "remove_stock(",
        "add_stock(",
    )

    for item in forbidden:
        assert item not in region


def test_http_gateway_does_not_serve_document_root_directly():
    source = Path(
        "app.py"
    ).read_text(
        encoding="utf-8"
    )

    marker = (
        "/api/document-attachments/"
        "<attachment_id>/content"
    )

    assert marker in source

    start = source.index(marker)

    region = source[
        max(0, start - 3000):
        start + 10000
    ]

    forbidden = (
        "send_from_directory("
        '"data/documents"',
        "send_from_directory("
        "'data/documents'",
        'Path("data/documents") /',
        "Path('data/documents') /",
    )

    for item in forbidden:
        assert item not in region


def test_content_gateway_uses_document_storage_authority():
    source = Path(
        "app.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        ".resolve("
        in source
        or "document_storage"
        in source
        or "InvoiceDocumentStorage"
        in source
    )


def test_document_001d_does_not_modify_frontend_contract():
    api_source = Path(
        "web/js/api.js"
    ).read_text(
        encoding="utf-8"
    )

    app_source = Path(
        "web/js/app.js"
    ).read_text(
        encoding="utf-8"
    )

    markers = (
        "/api/document-attachments/",
        "/api/audit-events/",
    )

    for marker in markers:
        assert marker not in api_source
        assert marker not in app_source
