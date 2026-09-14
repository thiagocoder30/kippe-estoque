import hashlib
import importlib
import os
from pathlib import Path

import pytest


MAX_DOCUMENT_BYTES = (
    10 * 1024 * 1024
)


PDF_BYTES = (
    b"%PDF-1.7\n"
    b"1 0 obj\n"
    b"<< /Type /Catalog >>\n"
    b"endobj\n"
    b"%%EOF\n"
)

JPEG_BYTES = (
    b"\xff\xd8\xff\xe0"
    b"\x00\x10JFIF\x00"
    b"\x01\x01\x00"
    b"\x00\x01\x00\x01"
    b"\x00\x00"
    b"\xff\xd9"
)

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01"
    b"\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00"
)


def _storage_class():
    module = importlib.import_module(
        "src.infrastructure.document_storage"
    )

    return module.InvoiceDocumentStorage


def _storage_error():
    module = importlib.import_module(
        "src.infrastructure.document_storage"
    )

    return module.DocumentStorageError


def _new_storage(
    tmp_path,
    *,
    max_bytes=MAX_DOCUMENT_BYTES,
):
    cls = _storage_class()

    return cls(
        root_path=tmp_path / "documents",
        max_bytes=max_bytes,
    )


def _store(
    storage,
    content,
    *,
    filename,
    declared_mime_type,
):
    return storage.store(
        content=content,
        original_filename=filename,
        declared_mime_type=declared_mime_type,
    )


def test_storage_accepts_valid_pdf(
    tmp_path,
):
    storage = _new_storage(
        tmp_path
    )

    descriptor = _store(
        storage,
        PDF_BYTES,
        filename="nota-fiscal.pdf",
        declared_mime_type="application/pdf",
    )

    assert descriptor[
        "mime_type"
    ] == "application/pdf"

    assert descriptor[
        "stored_filename"
    ].endswith(
        ".pdf"
    )

    assert descriptor[
        "byte_size"
    ] == len(PDF_BYTES)

    assert descriptor[
        "sha256"
    ] == hashlib.sha256(
        PDF_BYTES
    ).hexdigest()


def test_storage_accepts_valid_jpeg(
    tmp_path,
):
    storage = _new_storage(
        tmp_path
    )

    descriptor = _store(
        storage,
        JPEG_BYTES,
        filename="nota.jpg",
        declared_mime_type="image/jpeg",
    )

    assert descriptor[
        "mime_type"
    ] == "image/jpeg"

    assert descriptor[
        "stored_filename"
    ].endswith(
        ".jpg"
    )


def test_storage_accepts_valid_png(
    tmp_path,
):
    storage = _new_storage(
        tmp_path
    )

    descriptor = _store(
        storage,
        PNG_BYTES,
        filename="nota.png",
        declared_mime_type="image/png",
    )

    assert descriptor[
        "mime_type"
    ] == "image/png"

    assert descriptor[
        "stored_filename"
    ].endswith(
        ".png"
    )


def test_physical_file_contains_exact_original_bytes(
    tmp_path,
):
    storage = _new_storage(
        tmp_path
    )

    descriptor = _store(
        storage,
        PDF_BYTES,
        filename="nf.pdf",
        declared_mime_type="application/pdf",
    )

    physical = (
        storage.root_path
        / descriptor[
            "relative_path"
        ]
    )

    assert physical.read_bytes() == PDF_BYTES


def test_attachment_id_is_system_generated_and_not_filename(
    tmp_path,
):
    storage = _new_storage(
        tmp_path
    )

    descriptor = _store(
        storage,
        PDF_BYTES,
        filename="../../NF 123.pdf",
        declared_mime_type="application/pdf",
    )

    assert descriptor[
        "attachment_id"
    ]

    assert (
        descriptor[
            "attachment_id"
        ]
        not in {
            "../../NF 123.pdf",
            "NF 123.pdf",
        }
    )

    assert ".." not in descriptor[
        "stored_filename"
    ]

    assert "/" not in descriptor[
        "stored_filename"
    ]

    assert "\\" not in descriptor[
        "stored_filename"
    ]


def test_original_filename_is_metadata_only(
    tmp_path,
):
    storage = _new_storage(
        tmp_path
    )

    original = (
        "../../fornecedor/"
        "nota perigosa.pdf"
    )

    descriptor = _store(
        storage,
        PDF_BYTES,
        filename=original,
        declared_mime_type="application/pdf",
    )

    assert descriptor[
        "original_filename"
    ] == original

    assert (
        original
        not in descriptor[
            "relative_path"
        ]
    )


def test_relative_path_is_year_month_and_system_filename_only(
    tmp_path,
):
    storage = _new_storage(
        tmp_path
    )

    descriptor = _store(
        storage,
        PDF_BYTES,
        filename="nf.pdf",
        declared_mime_type="application/pdf",
    )

    relative = Path(
        descriptor[
            "relative_path"
        ]
    )

    assert not relative.is_absolute()

    assert ".." not in relative.parts

    assert len(
        relative.parts
    ) == 3

    assert (
        len(relative.parts[0])
        == 4
        and relative.parts[0].isdigit()
    )

    assert (
        len(relative.parts[1])
        == 2
        and relative.parts[1].isdigit()
    )

    assert (
        relative.parts[2]
        == descriptor[
            "stored_filename"
        ]
    )


def test_storage_rejects_unknown_file_signature(
    tmp_path,
):
    storage = _new_storage(
        tmp_path
    )

    error = _storage_error()

    with pytest.raises(
        error
    ):
        _store(
            storage,
            b"MZ malicious or unsupported",
            filename="nota.pdf",
            declared_mime_type="application/pdf",
        )


def test_storage_rejects_spoofed_extension(
    tmp_path,
):
    storage = _new_storage(
        tmp_path
    )

    error = _storage_error()

    with pytest.raises(
        error
    ):
        _store(
            storage,
            JPEG_BYTES,
            filename="imagem.pdf",
            declared_mime_type="image/jpeg",
        )


def test_storage_rejects_spoofed_declared_mime_type(
    tmp_path,
):
    storage = _new_storage(
        tmp_path
    )

    error = _storage_error()

    with pytest.raises(
        error
    ):
        _store(
            storage,
            PDF_BYTES,
            filename="nota.pdf",
            declared_mime_type="image/png",
        )


def test_storage_rejects_unsupported_extension_even_with_valid_signature(
    tmp_path,
):
    storage = _new_storage(
        tmp_path
    )

    error = _storage_error()

    with pytest.raises(
        error
    ):
        _store(
            storage,
            PDF_BYTES,
            filename="nota.exe",
            declared_mime_type="application/pdf",
        )


def test_storage_rejects_empty_file(
    tmp_path,
):
    storage = _new_storage(
        tmp_path
    )

    error = _storage_error()

    with pytest.raises(
        error
    ):
        _store(
            storage,
            b"",
            filename="nota.pdf",
            declared_mime_type="application/pdf",
        )


def test_storage_rejects_file_larger_than_service_limit(
    tmp_path,
):
    storage = _new_storage(
        tmp_path,
        max_bytes=32,
    )

    error = _storage_error()

    content = (
        b"%PDF-1.7\n"
        + b"x" * 64
    )

    with pytest.raises(
        error
    ):
        _store(
            storage,
            content,
            filename="grande.pdf",
            declared_mime_type="application/pdf",
        )


def test_storage_uses_atomic_replace_and_leaves_no_part_file(
    tmp_path,
):
    storage = _new_storage(
        tmp_path
    )

    descriptor = _store(
        storage,
        PDF_BYTES,
        filename="nf.pdf",
        declared_mime_type="application/pdf",
    )

    physical = (
        storage.root_path
        / descriptor[
            "relative_path"
        ]
    )

    assert physical.exists()

    leftovers = list(
        storage.root_path.rglob(
            "*.part"
        )
    )

    assert leftovers == []


def test_failed_atomic_replace_cleans_partial_file(
    tmp_path,
    monkeypatch,
):
    storage = _new_storage(
        tmp_path
    )

    module = importlib.import_module(
        "src.infrastructure.document_storage"
    )

    real_replace = os.replace

    def failing_replace(
        source,
        destination,
    ):
        raise OSError(
            "simulated atomic replace failure"
        )

    monkeypatch.setattr(
        module.os,
        "replace",
        failing_replace,
    )

    error = _storage_error()

    with pytest.raises(
        error
    ):
        _store(
            storage,
            PDF_BYTES,
            filename="falha.pdf",
            declared_mime_type="application/pdf",
        )

    assert list(
        storage.root_path.rglob(
            "*.part"
        )
    ) == []

    final_documents = [
        path
        for path
        in storage.root_path.rglob("*")
        if (
            path.is_file()
            and not path.name.endswith(
                ".part"
            )
        )
    ]

    assert final_documents == []

    monkeypatch.setattr(
        module.os,
        "replace",
        real_replace,
    )


def test_resolve_rejects_absolute_and_traversal_paths(
    tmp_path,
):
    storage = _new_storage(
        tmp_path
    )

    error = _storage_error()

    with pytest.raises(
        error
    ):
        storage.resolve(
            "/etc/passwd"
        )

    with pytest.raises(
        error
    ):
        storage.resolve(
            "../../outside.pdf"
        )


def test_resolve_returns_only_files_inside_storage_root(
    tmp_path,
):
    storage = _new_storage(
        tmp_path
    )

    descriptor = _store(
        storage,
        PNG_BYTES,
        filename="nf.png",
        declared_mime_type="image/png",
    )

    resolved = storage.resolve(
        descriptor[
            "relative_path"
        ]
    )

    assert resolved.exists()

    assert resolved.is_file()

    assert (
        storage.root_path.resolve()
        in resolved.resolve().parents
    )


def test_delete_removes_only_managed_document(
    tmp_path,
):
    storage = _new_storage(
        tmp_path
    )

    descriptor = _store(
        storage,
        PDF_BYTES,
        filename="nf.pdf",
        declared_mime_type="application/pdf",
    )

    physical = storage.resolve(
        descriptor[
            "relative_path"
        ]
    )

    assert physical.exists()

    storage.delete(
        descriptor[
            "relative_path"
        ]
    )

    assert not physical.exists()


def test_delete_rejects_path_outside_storage_root(
    tmp_path,
):
    storage = _new_storage(
        tmp_path
    )

    error = _storage_error()

    with pytest.raises(
        error
    ):
        storage.delete(
            "../../outside.pdf"
        )


def test_storage_contract_has_no_sqlite_or_product_authority_dependency():
    source_path = Path(
        "src/infrastructure/document_storage.py"
    )

    assert source_path.exists()

    source = source_path.read_text(
        encoding="utf-8"
    )

    forbidden = (
        "sqlite3",
        "SQLiteProductRepository",
        "Product(",
        "Batch(",
        "UPDATE products",
        "UPDATE batches",
        "document_attachments",
    )

    for marker in forbidden:
        assert marker not in source
