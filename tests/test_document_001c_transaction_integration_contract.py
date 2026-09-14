from pathlib import Path
import sqlite3

import pytest

from src.interfaces.sqlite_repository import SQLiteProductRepository


PDF_BYTES = b"%PDF-1.7\nKIPPE DOCUMENT TEST\n%%EOF\n"


def make_repository(tmp_path):
    return SQLiteProductRepository(
        str(tmp_path / "document-001c.db")
    )


def seed_receiving_event(repository):
    return repository.append_operational_audit_event(
        event_type="RECEBIMENTO",
        product_id="SKU-DOC-001",
        batch_code="L-DOC-001",
        supplier="FORNECEDOR TESTE",
        document_id="NF-123",
        origin_document="NF",
        operator_id="1001",
        metadata={
            "test": "DOCUMENT-001C",
        },
    )


def test_repository_exposes_atomic_create_and_link_method(tmp_path):
    repository = make_repository(tmp_path)

    assert hasattr(
        repository,
        "create_and_link_document_attachment",
    )


def test_repository_atomic_method_creates_metadata_and_link(tmp_path):
    repository = make_repository(tmp_path)
    event_id = seed_receiving_event(repository)

    attachment_id = repository.create_and_link_document_attachment(
        event_id=event_id,
        attachment_id="DOC-ATOMIC-001",
        business_document_number="NF-123",
        supplier="FORNECEDOR TESTE",
        original_filename="nf123.pdf",
        stored_filename="DOC-ATOMIC-001.pdf",
        relative_path="2026/09/DOC-ATOMIC-001.pdf",
        mime_type="application/pdf",
        byte_size=len(PDF_BYTES),
        sha256="a" * 64,
        operator_id="1001",
    )

    assert attachment_id == "DOC-ATOMIC-001"

    metadata = repository.get_document_attachment(
        "DOC-ATOMIC-001"
    )

    assert metadata is not None
    assert metadata["id"] == "DOC-ATOMIC-001"

    linked = repository.get_document_attachments_by_event(
        event_id
    )

    assert len(linked) == 1
    assert linked[0]["id"] == "DOC-ATOMIC-001"


def test_repository_atomic_method_rejects_non_receiving_event(tmp_path):
    repository = make_repository(tmp_path)

    event_id = repository.append_operational_audit_event(
        event_type="PUTAWAY",
        product_id="SKU-DOC-002",
        batch_code="L-DOC-002",
        operator_id="1001",
    )

    with pytest.raises(ValueError):
        repository.create_and_link_document_attachment(
            event_id=event_id,
            attachment_id="DOC-ATOMIC-002",
            original_filename="nf.pdf",
            stored_filename="DOC-ATOMIC-002.pdf",
            relative_path="2026/09/DOC-ATOMIC-002.pdf",
            mime_type="application/pdf",
            byte_size=len(PDF_BYTES),
            sha256="b" * 64,
            operator_id="1001",
        )

    assert repository.get_document_attachment(
        "DOC-ATOMIC-002"
    ) is None


def test_repository_atomic_method_rolls_back_metadata_if_link_insert_fails(
    tmp_path,
    monkeypatch,
):
    repository = make_repository(tmp_path)
    event_id = seed_receiving_event(repository)

    original_get_connection = repository._get_connection

    class FailingConnection:
        def __init__(self, conn):
            self._conn = conn

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self._conn.close()

        def execute(self, sql, params=()):
            if (
                "INSERT INTO operational_audit_event_attachments"
                in sql
            ):
                raise RuntimeError(
                    "forced link failure"
                )

            return self._conn.execute(
                sql,
                params,
            )

        def commit(self):
            return self._conn.commit()

        def rollback(self):
            return self._conn.rollback()

    def failing_get_connection():
        return FailingConnection(
            original_get_connection()
        )

    monkeypatch.setattr(
        repository,
        "_get_connection",
        failing_get_connection,
    )

    with pytest.raises(RuntimeError):
        repository.create_and_link_document_attachment(
            event_id=event_id,
            attachment_id="DOC-ROLLBACK-001",
            original_filename="rollback.pdf",
            stored_filename="DOC-ROLLBACK-001.pdf",
            relative_path="2026/09/DOC-ROLLBACK-001.pdf",
            mime_type="application/pdf",
            byte_size=len(PDF_BYTES),
            sha256="c" * 64,
            operator_id="1001",
        )

    monkeypatch.setattr(
        repository,
        "_get_connection",
        original_get_connection,
    )

    assert repository.get_document_attachment(
        "DOC-ROLLBACK-001"
    ) is None

    assert repository.get_document_attachments_by_event(
        event_id
    ) == []


def test_repository_atomic_method_uses_single_transaction_boundary():
    source = Path(
        "src/interfaces/sqlite_repository.py"
    ).read_text(
        encoding="utf-8"
    )

    marker = (
        "def create_and_link_document_attachment"
    )

    assert marker in source

    start = source.index(marker)
    region = source[start:start + 9000]

    assert "BEGIN IMMEDIATE" in region
    assert "conn.commit()" in region
    assert "conn.rollback()" in region

    assert (
        "self.create_document_attachment("
        not in region
    )

    assert (
        "self.link_document_attachment_to_audit_event("
        not in region
    )


def test_document_integration_use_case_module_exists():
    assert Path(
        "src/use_cases/document_attachment.py"
    ).exists()


def import_use_case():
    from src.use_cases.document_attachment import (
        AttachDocumentToAuditEventUseCase,
        DocumentAttachmentIntegrationError,
    )

    return (
        AttachDocumentToAuditEventUseCase,
        DocumentAttachmentIntegrationError,
    )


class FakeStorage:
    def __init__(
        self,
        descriptor=None,
        store_error=None,
        delete_error=None,
    ):
        self.descriptor = descriptor or {
            "attachment_id": "DOC-001",
            "original_filename": "nf.pdf",
            "stored_filename": "DOC-001.pdf",
            "relative_path": "2026/09/DOC-001.pdf",
            "mime_type": "application/pdf",
            "byte_size": len(PDF_BYTES),
            "sha256": "d" * 64,
        }

        self.store_error = store_error
        self.delete_error = delete_error
        self.store_calls = []
        self.delete_calls = []

    def store(
        self,
        *,
        content,
        original_filename,
        declared_mime_type,
    ):
        self.store_calls.append(
            {
                "content": content,
                "original_filename": original_filename,
                "declared_mime_type": declared_mime_type,
            }
        )

        if self.store_error:
            raise self.store_error

        return dict(self.descriptor)

    def delete(self, relative_path):
        self.delete_calls.append(
            relative_path
        )

        if self.delete_error:
            raise self.delete_error


class FakeRepository:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def create_and_link_document_attachment(
        self,
        **kwargs,
    ):
        self.calls.append(kwargs)

        if self.error:
            raise self.error

        return kwargs["attachment_id"]


def test_use_case_success_stores_file_then_persists_metadata_and_link():
    (
        UseCase,
        _,
    ) = import_use_case()

    storage = FakeStorage()
    repository = FakeRepository()

    use_case = UseCase(
        repository=repository,
        storage=storage,
    )

    result = use_case.attach(
        event_id=77,
        content=PDF_BYTES,
        original_filename="nota.pdf",
        declared_mime_type="application/pdf",
        business_document_number="NF-77",
        supplier="FORNECEDOR 77",
        operator_id="1001",
    )

    assert result["attachment_id"] == "DOC-001"
    assert len(storage.store_calls) == 1
    assert len(repository.calls) == 1
    assert storage.delete_calls == []


def test_use_case_forwards_storage_descriptor_without_reinventing_identity():
    (
        UseCase,
        _,
    ) = import_use_case()

    descriptor = {
        "attachment_id": "DOC-PHYSICAL-999",
        "original_filename": "original.jpeg",
        "stored_filename": "DOC-PHYSICAL-999.jpg",
        "relative_path": "2026/09/DOC-PHYSICAL-999.jpg",
        "mime_type": "image/jpeg",
        "byte_size": 123,
        "sha256": "9" * 64,
    }

    repository = FakeRepository()
    storage = FakeStorage(
        descriptor=descriptor
    )

    use_case = UseCase(
        repository=repository,
        storage=storage,
    )

    result = use_case.attach(
        event_id=88,
        content=b"\xff\xd8\xffpayload",
        original_filename="original.jpeg",
        declared_mime_type="image/jpeg",
        business_document_number="NF-88",
        supplier="FORNECEDOR 88",
        operator_id="1001",
    )

    call = repository.calls[0]

    for key, value in descriptor.items():
        assert call[key] == value

    assert result["attachment_id"] == (
        descriptor["attachment_id"]
    )


def test_storage_failure_creates_no_metadata():
    (
        UseCase,
        _,
    ) = import_use_case()

    storage = FakeStorage(
        store_error=RuntimeError(
            "storage failed"
        )
    )

    repository = FakeRepository()

    use_case = UseCase(
        repository=repository,
        storage=storage,
    )

    with pytest.raises(RuntimeError):
        use_case.attach(
            event_id=99,
            content=PDF_BYTES,
            original_filename="nf.pdf",
            declared_mime_type="application/pdf",
            operator_id="1001",
        )

    assert repository.calls == []
    assert storage.delete_calls == []


def test_repository_failure_compensates_physical_file():
    (
        UseCase,
        _,
    ) = import_use_case()

    storage = FakeStorage()

    repository = FakeRepository(
        error=RuntimeError(
            "database failed"
        )
    )

    use_case = UseCase(
        repository=repository,
        storage=storage,
    )

    with pytest.raises(RuntimeError):
        use_case.attach(
            event_id=100,
            content=PDF_BYTES,
            original_filename="nf.pdf",
            declared_mime_type="application/pdf",
            operator_id="1001",
        )

    assert storage.delete_calls == [
        "2026/09/DOC-001.pdf"
    ]


def test_compensation_failure_is_not_silently_hidden():
    (
        UseCase,
        IntegrationError,
    ) = import_use_case()

    storage = FakeStorage(
        delete_error=RuntimeError(
            "delete failed"
        )
    )

    repository = FakeRepository(
        error=RuntimeError(
            "database failed"
        )
    )

    use_case = UseCase(
        repository=repository,
        storage=storage,
    )

    with pytest.raises(
        IntegrationError
    ) as exc:
        use_case.attach(
            event_id=101,
            content=PDF_BYTES,
            original_filename="nf.pdf",
            declared_mime_type="application/pdf",
            operator_id="1001",
        )

    assert "compensa" in str(
        exc.value
    ).lower()


def test_use_case_requires_nonblank_operator_id():
    (
        UseCase,
        _,
    ) = import_use_case()

    use_case = UseCase(
        repository=FakeRepository(),
        storage=FakeStorage(),
    )

    with pytest.raises(ValueError):
        use_case.attach(
            event_id=1,
            content=PDF_BYTES,
            original_filename="nf.pdf",
            declared_mime_type="application/pdf",
            operator_id="",
        )


def test_use_case_requires_positive_event_id():
    (
        UseCase,
        _,
    ) = import_use_case()

    use_case = UseCase(
        repository=FakeRepository(),
        storage=FakeStorage(),
    )

    with pytest.raises(ValueError):
        use_case.attach(
            event_id=0,
            content=PDF_BYTES,
            original_filename="nf.pdf",
            declared_mime_type="application/pdf",
            operator_id="1001",
        )


def test_integration_module_has_no_product_or_batch_authority():
    source = Path(
        "src/use_cases/document_attachment.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden = (
        "Product(",
        "Batch(",
        "quantity",
        "save_product",
        "remove_stock",
        "add_stock",
    )

    for marker in forbidden:
        assert marker not in source


def test_document_001c_contract_does_not_add_http_gateway():
    app_source = Path(
        "app.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "/api/documents"
        not in app_source
    )

    assert (
        "/api/document"
        not in app_source
    )
