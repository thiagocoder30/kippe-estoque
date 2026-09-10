import sqlite3
from pathlib import Path

import pytest

from src.interfaces.sqlite_repository import (
    SQLiteProductRepository,
)


DB_PATH = Path(
    "data/document_001a_contract.db"
)


@pytest.fixture
def repository():
    DB_PATH.unlink(
        missing_ok=True
    )

    repository = (
        SQLiteProductRepository(
            str(DB_PATH)
        )
    )

    yield repository

    DB_PATH.unlink(
        missing_ok=True
    )


def _columns(table_name):
    with sqlite3.connect(
        DB_PATH
    ) as connection:
        return {
            row[1]: row[2]
            for row in connection.execute(
                f"PRAGMA table_info('{table_name}')"
            ).fetchall()
        }


def _table_sql(table_name):
    with sqlite3.connect(
        DB_PATH
    ) as connection:
        row = connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type='table'
              AND name=?
            """,
            (
                table_name,
            ),
        ).fetchone()

    return (
        row[0]
        if row
        else ""
    )


def _append_receiving(
    repository,
    *,
    product_id,
    invoice_number,
):
    return (
        repository
        .append_operational_audit_event(
            event_type="RECEBIMENTO",
            product_id=product_id,
            batch_code="L001",
            supplier="FORNECEDOR TESTE",
            document_id=invoice_number,
            origin_document="MANUAL",
            operator_id="1001",
        )
    )


def test_document_attachment_table_exists(
    repository,
):
    columns = _columns(
        "document_attachments"
    )

    assert columns


def test_document_attachment_table_has_required_metadata(
    repository,
):
    columns = _columns(
        "document_attachments"
    )

    required = {
        "id",
        "business_document_number",
        "supplier",
        "original_filename",
        "stored_filename",
        "relative_path",
        "mime_type",
        "byte_size",
        "sha256",
        "uploaded_at",
        "operator_id",
    }

    assert required.issubset(
        columns
    )


def test_document_attachment_table_contains_no_blob_column(
    repository,
):
    columns = _columns(
        "document_attachments"
    )

    assert columns

    assert all(
        str(column_type)
        .upper()
        != "BLOB"
        for column_type
        in columns.values()
    )


def test_event_attachment_link_table_exists(
    repository,
):
    columns = _columns(
        "operational_audit_event_attachments"
    )

    required = {
        "event_id",
        "attachment_id",
        "linked_at",
        "operator_id",
    }

    assert required.issubset(
        columns
    )


def test_event_attachment_link_is_composite_unique(
    repository,
):
    sql = _table_sql(
        "operational_audit_event_attachments"
    ).replace(
        "\n",
        " "
    ).upper()

    assert (
        "PRIMARY KEY"
        in sql
    )

    assert (
        "EVENT_ID"
        in sql
        and
        "ATTACHMENT_ID"
        in sql
    )


def test_repository_can_create_document_attachment(
    repository,
):
    attachment_id = (
        repository
        .create_document_attachment(
            attachment_id="DOC-001",
            business_document_number="NF-123",
            supplier="FORNECEDOR A",
            original_filename="nf-123.pdf",
            stored_filename="DOC-001.pdf",
            relative_path=(
                "documents/invoices/"
                "2026/09/DOC-001.pdf"
            ),
            mime_type="application/pdf",
            byte_size=12345,
            sha256=(
                "a" * 64
            ),
            operator_id="1001",
        )
    )

    assert attachment_id == "DOC-001"


def test_repository_reads_document_attachment(
    repository,
):
    repository.create_document_attachment(
        attachment_id="DOC-002",
        business_document_number="NF-456",
        supplier="FORNECEDOR B",
        original_filename="nota.pdf",
        stored_filename="DOC-002.pdf",
        relative_path=(
            "documents/invoices/"
            "2026/09/DOC-002.pdf"
        ),
        mime_type="application/pdf",
        byte_size=4321,
        sha256="b" * 64,
        operator_id="1001",
    )

    attachment = (
        repository
        .get_document_attachment(
            "DOC-002"
        )
    )

    assert attachment[
        "id"
    ] == "DOC-002"

    assert attachment[
        "business_document_number"
    ] == "NF-456"

    assert attachment[
        "supplier"
    ] == "FORNECEDOR B"

    assert attachment[
        "relative_path"
    ].endswith(
        "DOC-002.pdf"
    )

    assert attachment[
        "mime_type"
    ] == "application/pdf"

    assert attachment[
        "byte_size"
    ] == 4321

    assert attachment[
        "sha256"
    ] == "b" * 64

    assert attachment[
        "operator_id"
    ] == "1001"


def test_one_attachment_can_link_to_multiple_receiving_events(
    repository,
):
    event_a = _append_receiving(
        repository,
        product_id="SKU-A",
        invoice_number="NF-900",
    )

    event_b = _append_receiving(
        repository,
        product_id="SKU-B",
        invoice_number="NF-900",
    )

    repository.create_document_attachment(
        attachment_id="DOC-SHARED",
        business_document_number="NF-900",
        supplier="FORNECEDOR COMPARTILHADO",
        original_filename="nf-900.pdf",
        stored_filename="DOC-SHARED.pdf",
        relative_path=(
            "documents/invoices/"
            "2026/09/DOC-SHARED.pdf"
        ),
        mime_type="application/pdf",
        byte_size=5000,
        sha256="c" * 64,
        operator_id="1001",
    )

    repository.link_document_attachment_to_audit_event(
        event_id=event_a,
        attachment_id="DOC-SHARED",
        operator_id="1001",
    )

    repository.link_document_attachment_to_audit_event(
        event_id=event_b,
        attachment_id="DOC-SHARED",
        operator_id="1001",
    )

    attachments_a = (
        repository
        .get_document_attachments_by_event(
            event_a
        )
    )

    attachments_b = (
        repository
        .get_document_attachments_by_event(
            event_b
        )
    )

    assert [
        item["id"]
        for item in attachments_a
    ] == [
        "DOC-SHARED"
    ]

    assert [
        item["id"]
        for item in attachments_b
    ] == [
        "DOC-SHARED"
    ]


def test_same_event_attachment_link_cannot_be_duplicated(
    repository,
):
    event_id = _append_receiving(
        repository,
        product_id="SKU-C",
        invoice_number="NF-901",
    )

    repository.create_document_attachment(
        attachment_id="DOC-UNIQUE-LINK",
        business_document_number="NF-901",
        supplier="FORNECEDOR C",
        original_filename="nf.pdf",
        stored_filename="DOC-UNIQUE-LINK.pdf",
        relative_path=(
            "documents/invoices/"
            "2026/09/DOC-UNIQUE-LINK.pdf"
        ),
        mime_type="application/pdf",
        byte_size=100,
        sha256="d" * 64,
        operator_id="1001",
    )

    repository.link_document_attachment_to_audit_event(
        event_id=event_id,
        attachment_id="DOC-UNIQUE-LINK",
        operator_id="1001",
    )

    with pytest.raises(
        sqlite3.IntegrityError
    ):
        repository.link_document_attachment_to_audit_event(
            event_id=event_id,
            attachment_id="DOC-UNIQUE-LINK",
            operator_id="1001",
        )


def test_attachment_can_be_linked_after_receiving_event_exists(
    repository,
):
    event_id = _append_receiving(
        repository,
        product_id="SKU-LATE",
        invoice_number="NF-LATE",
    )

    repository.create_document_attachment(
        attachment_id="DOC-LATE",
        business_document_number="NF-LATE",
        supplier="FORNECEDOR LATE",
        original_filename="late.pdf",
        stored_filename="DOC-LATE.pdf",
        relative_path=(
            "documents/invoices/"
            "2026/09/DOC-LATE.pdf"
        ),
        mime_type="application/pdf",
        byte_size=789,
        sha256="e" * 64,
        operator_id="1001",
    )

    repository.link_document_attachment_to_audit_event(
        event_id=event_id,
        attachment_id="DOC-LATE",
        operator_id="1001",
    )

    attachments = (
        repository
        .get_document_attachments_by_event(
            event_id
        )
    )

    assert len(
        attachments
    ) == 1

    assert attachments[0][
        "id"
    ] == "DOC-LATE"


def test_attachment_link_requires_existing_audit_event(
    repository,
):
    repository.create_document_attachment(
        attachment_id="DOC-ORPHAN",
        business_document_number="NF-X",
        supplier="FORNECEDOR X",
        original_filename="x.pdf",
        stored_filename="DOC-ORPHAN.pdf",
        relative_path=(
            "documents/invoices/"
            "2026/09/DOC-ORPHAN.pdf"
        ),
        mime_type="application/pdf",
        byte_size=1,
        sha256="f" * 64,
        operator_id="1001",
    )

    with pytest.raises(
        (
            ValueError,
            sqlite3.IntegrityError,
        )
    ):
        repository.link_document_attachment_to_audit_event(
            event_id=999999,
            attachment_id="DOC-ORPHAN",
            operator_id="1001",
        )


def test_attachment_link_requires_receiving_event(
    repository,
):
    event_id = (
        repository
        .append_operational_audit_event(
            event_type="PUTAWAY",
            product_id="SKU-PUT",
            batch_code="L001",
            location_id="A-01",
            operator_id="1001",
        )
    )

    repository.create_document_attachment(
        attachment_id="DOC-PUT",
        business_document_number="NF-PUT",
        supplier="FORNECEDOR",
        original_filename="put.pdf",
        stored_filename="DOC-PUT.pdf",
        relative_path=(
            "documents/invoices/"
            "2026/09/DOC-PUT.pdf"
        ),
        mime_type="application/pdf",
        byte_size=1,
        sha256="1" * 64,
        operator_id="1001",
    )

    with pytest.raises(
        ValueError,
        match="RECEBIMENTO",
    ):
        repository.link_document_attachment_to_audit_event(
            event_id=event_id,
            attachment_id="DOC-PUT",
            operator_id="1001",
        )


def test_commercial_document_id_remains_on_receiving_event(
    repository,
):
    event_id = _append_receiving(
        repository,
        product_id="SKU-COMMERCIAL",
        invoice_number="NF-COMMERCIAL-777",
    )

    events = (
        repository
        .get_operational_audit_events_by_product(
            "SKU-COMMERCIAL"
        )
    )

    assert len(events) == 1

    assert events[0][
        "id"
    ] == event_id

    assert events[0][
        "document_id"
    ] == "NF-COMMERCIAL-777"

    assert (
        events[0][
            "document_id"
        ]
        != "DOC-TECHNICAL"
    )


def test_document_attachment_does_not_mutate_product_stock(
    repository,
):
    source = Path(
        "src/interfaces/sqlite_repository.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "document_attachments"
        in source
    )

    assert (
        "operational_audit_event_attachments"
        in source
    )

    document_region = source[
        source.index(
            "def create_document_attachment"
        ):
        source.index(
            "def get_document_attachment"
        )
    ]

    forbidden = (
        "UPDATE products",
        "UPDATE batches",
        "_save_product_on_connection",
    )

    for marker in forbidden:
        assert marker not in document_region
