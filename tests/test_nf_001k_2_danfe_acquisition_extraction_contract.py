"""
NF-001K.2 — Real DANFE Acquisition & Extraction Contract

RED contract.

This milestone defines the anti-corruption boundary between:

    physical DANFE evidence
        ->
    document acquisition
        ->
    extraction result
        ->
    mandatory human review
        ->
    existing ExtractedSupplierInvoice / InvoicePreparationService

It MUST NOT:

* mutate stock;
* execute receiving;
* register products automatically;
* reconcile products automatically;
* make OCR output authoritative;
* depend on a concrete OCR/AI provider;
* modify J.8/J.9/J.10 receiving authority.
"""

from __future__ import annotations

import hashlib
import importlib
from dataclasses import fields, is_dataclass


MODULE_NAME = (
    "src.application.procurement."
    "danfe_acquisition"
)


def load_module():
    return importlib.import_module(MODULE_NAME)


def public_field_names(cls):
    assert is_dataclass(cls)
    return {field.name for field in fields(cls)}


def test_module_exists():
    module = load_module()
    assert module is not None


def test_contract_exports_required_types():
    module = load_module()

    required = {
        "DanfeDocument",
        "DanfeAcquisitionMetadata",
        "ExtractedInvoiceField",
        "ExtractedInvoiceLine",
        "InvoiceExtractionResult",
        "ReviewedInvoiceExtraction",
        "DanfeAcquisitionError",
        "InvoiceExtractionError",
        "InvoiceReviewError",
    }

    missing = sorted(
        name
        for name in required
        if not hasattr(module, name)
    )

    assert not missing, (
        "NF-001K.2 missing public contracts: "
        + ", ".join(missing)
    )


def test_danfe_document_is_immutable_value_object():
    module = load_module()
    cls = module.DanfeDocument

    assert is_dataclass(cls)

    params = cls.__dataclass_params__
    assert params.frozen is True

    names = public_field_names(cls)

    assert {
        "content",
        "filename",
        "mime_type",
        "sha256",
        "metadata",
    }.issubset(names)


def test_danfe_metadata_is_explicit_and_immutable():
    module = load_module()
    cls = module.DanfeAcquisitionMetadata

    assert is_dataclass(cls)
    assert cls.__dataclass_params__.frozen is True

    names = public_field_names(cls)

    assert {
        "source",
        "operator_id",
        "acquired_at",
    }.issubset(names)


def test_danfe_document_rejects_empty_content():
    module = load_module()

    metadata = module.DanfeAcquisitionMetadata(
        source="CAMERA",
        operator_id="operator-1",
        acquired_at="2026-09-17T17:00:00-03:00",
    )

    try:
        module.DanfeDocument(
            content=b"",
            filename="danfe.jpg",
            mime_type="image/jpeg",
            sha256=hashlib.sha256(b"").hexdigest(),
            metadata=metadata,
        )
    except module.DanfeAcquisitionError:
        return

    raise AssertionError(
        "Empty DANFE evidence must be rejected."
    )


def test_danfe_document_rejects_non_image_mime():
    module = load_module()

    content = b"fake-danfe"

    metadata = module.DanfeAcquisitionMetadata(
        source="CAMERA",
        operator_id="operator-1",
        acquired_at="2026-09-17T17:00:00-03:00",
    )

    try:
        module.DanfeDocument(
            content=content,
            filename="danfe.txt",
            mime_type="text/plain",
            sha256=hashlib.sha256(content).hexdigest(),
            metadata=metadata,
        )
    except module.DanfeAcquisitionError:
        return

    raise AssertionError(
        "NF-001K.2 must reject non-image evidence."
    )


def test_danfe_document_verifies_sha256_integrity():
    module = load_module()

    content = b"real-image-evidence"

    metadata = module.DanfeAcquisitionMetadata(
        source="CAMERA",
        operator_id="operator-1",
        acquired_at="2026-09-17T17:00:00-03:00",
    )

    try:
        module.DanfeDocument(
            content=content,
            filename="danfe.jpg",
            mime_type="image/jpeg",
            sha256="0" * 64,
            metadata=metadata,
        )
    except module.DanfeAcquisitionError:
        return

    raise AssertionError(
        "DANFE evidence hash must match its bytes."
    )


def test_extracted_field_preserves_value_confidence_and_review_state():
    module = load_module()
    cls = module.ExtractedInvoiceField

    assert is_dataclass(cls)
    assert cls.__dataclass_params__.frozen is True

    names = public_field_names(cls)

    assert {
        "value",
        "confidence",
        "requires_review",
    }.issubset(names)


def test_extracted_line_converges_to_existing_fiscal_contract():
    module = load_module()
    cls = module.ExtractedInvoiceLine

    assert is_dataclass(cls)
    assert cls.__dataclass_params__.frozen is True

    names = public_field_names(cls)

    required = {
        "supplier_product_code",
        "description",
        "gtin",
        "commercial_unit",
        "quantity",
        "unit_price",
    }

    assert required.issubset(names)


def test_extraction_result_preserves_document_identity():
    module = load_module()
    cls = module.InvoiceExtractionResult

    assert is_dataclass(cls)
    assert cls.__dataclass_params__.frozen is True

    names = public_field_names(cls)

    assert {
        "document_sha256",
        "invoice_number",
        "supplier_id",
        "lines",
        "extractor",
        "requires_review",
    }.issubset(names)


def test_extraction_result_is_not_authoritative_by_default():
    module = load_module()

    field = module.ExtractedInvoiceField(
        value="123",
        confidence=0.99,
        requires_review=False,
    )

    line = module.ExtractedInvoiceLine(
        supplier_product_code=field,
        description=field,
        gtin=field,
        commercial_unit=field,
        quantity=field,
        unit_price=field,
    )

    result = module.InvoiceExtractionResult(
        document_sha256="a" * 64,
        invoice_number=field,
        supplier_id=field,
        lines=(line,),
        extractor="TEST_EXTRACTOR",
        requires_review=True,
    )

    assert result.requires_review is True

    assert not hasattr(
        result,
        "receive"
    )

    assert not hasattr(
        result,
        "execute_receiving"
    )

    assert not hasattr(
        result,
        "mutate_stock"
    )


def test_confidence_is_bounded_between_zero_and_one():
    module = load_module()

    invalid_values = (
        -0.01,
        1.01,
    )

    for confidence in invalid_values:
        try:
            module.ExtractedInvoiceField(
                value="x",
                confidence=confidence,
                requires_review=True,
            )
        except module.InvoiceExtractionError:
            continue

        raise AssertionError(
            "Extraction confidence must remain "
            "between 0.0 and 1.0."
        )


def test_human_review_is_a_distinct_contract():
    module = load_module()
    cls = module.ReviewedInvoiceExtraction

    assert is_dataclass(cls)
    assert cls.__dataclass_params__.frozen is True

    names = public_field_names(cls)

    assert {
        "document_sha256",
        "invoice_number",
        "supplier_id",
        "lines",
        "reviewed_by",
        "reviewed_at",
    }.issubset(names)


def test_reviewed_line_contract_still_matches_invoice_preparation():
    module = load_module()

    reviewed_cls = module.ReviewedInvoiceExtraction

    annotations = getattr(
        reviewed_cls,
        "__annotations__",
        {},
    )

    assert "invoice_number" in annotations
    assert "supplier_id" in annotations
    assert "lines" in annotations


def test_contract_contains_no_stock_or_receiving_authority():
    module = load_module()

    forbidden_exports = {
        "StockMutation",
        "StockMutationService",
        "ReceiveGoodsService",
        "ReceivingExecution",
        "ReceivingPersistence",
        "ProductRegistrationService",
    }

    exported = set(dir(module))

    assert forbidden_exports.isdisjoint(exported)


def test_contract_does_not_require_specific_ai_provider():
    module = load_module()

    source = open(
        module.__file__,
        "r",
        encoding="utf-8",
    ).read().lower()

    forbidden = (
        "import openai",
        "from openai",
        "import anthropic",
        "from anthropic",
        "google.generativeai",
        "pytesseract",
        "import cv2",
        "from cv2",
    )

    for marker in forbidden:
        assert marker not in source


def test_contract_does_not_import_receiving_execution():
    module = load_module()

    source = open(
        module.__file__,
        "r",
        encoding="utf-8",
    ).read()

    forbidden = (
        "receiving_execution",
        "receiving_persistence",
        "LiveFinancialAuthority",
    )

    for marker in forbidden:
        assert marker not in source


def test_reviewed_contract_can_represent_existing_preparation_payload():
    module = load_module()

    line = {
        "supplier_product_code": "FORN-001",
        "description": "PRODUTO TESTE",
        "gtin": "7891234567890",
        "commercial_unit": "UN",
        "quantity": 10,
        "unit_price": 5.5,
    }

    reviewed = module.ReviewedInvoiceExtraction(
        document_sha256="b" * 64,
        invoice_number="NF-123",
        supplier_id="SUP-001",
        lines=(line,),
        reviewed_by="operator-1",
        reviewed_at="2026-09-17T17:00:00-03:00",
    )

    assert reviewed.invoice_number == "NF-123"
    assert reviewed.supplier_id == "SUP-001"
    assert reviewed.lines[0]["quantity"] == 10
    assert reviewed.lines[0]["unit_price"] == 5.5
