"""
NF-001K.4B — Provider-Neutral DANFE Extraction Port

RED contract.

This milestone introduces the application port that future OCR,
multimodal-AI or other document extraction providers must implement.

The port deliberately has no concrete provider implementation.

Architecture:

    DanfeDocument
        ->
    DanfeInvoiceExtractor
        ->
    InvoiceExtractionResult
        ->
    mandatory human review

It MUST NOT:

* depend on OpenAI, Gemini, Google Vision, Tesseract or another provider;
* perform HTTP requests;
* mutate stock;
* execute receiving;
* persist receiving mutations;
* reconcile catalog identities;
* register products;
* bypass human review;
* make machine extraction authoritative.
"""

from __future__ import annotations

import importlib
import inspect
from dataclasses import fields, is_dataclass


MODULE_NAME = (
    "src.application.procurement."
    "danfe_extraction"
)

ACQUISITION_MODULE = (
    "src.application.procurement."
    "danfe_acquisition"
)


def load_module():
    return importlib.import_module(MODULE_NAME)


def load_acquisition_module():
    return importlib.import_module(ACQUISITION_MODULE)


def field_names(cls):
    assert is_dataclass(cls)
    return {
        field.name
        for field in fields(cls)
    }


def test_extraction_port_module_exists():
    module = load_module()
    assert module is not None


def test_extraction_port_exports_required_public_contracts():
    module = load_module()

    required = {
        "DanfeInvoiceExtractor",
        "ExtractionRequest",
        "ExtractionFailure",
        "ExtractionFailureCode",
    }

    missing = sorted(
        name
        for name in required
        if not hasattr(module, name)
    )

    assert not missing, (
        "NF-001K.4B missing public contracts: "
        + ", ".join(missing)
    )


def test_extraction_request_is_immutable():
    module = load_module()

    cls = module.ExtractionRequest

    assert is_dataclass(cls)
    assert cls.__dataclass_params__.frozen is True


def test_extraction_request_has_only_canonical_input_and_context():
    module = load_module()

    names = field_names(
        module.ExtractionRequest
    )

    assert {
        "document",
        "requested_by",
    }.issubset(names)

    forbidden = {
        "api_key",
        "provider",
        "model",
        "stock_id",
        "warehouse_id",
        "receiving_id",
        "product_id",
    }

    assert names.isdisjoint(forbidden)


def test_extraction_request_requires_canonical_danfe_document():
    module = load_module()
    acquisition = load_acquisition_module()

    metadata = acquisition.DanfeAcquisitionMetadata(
        source="HTTP_UPLOAD",
        operator_id="OP-K4B",
        acquired_at="2026-09-18T09:00:00-03:00",
    )

    document = acquisition.DanfeDocument(
        content=b"fake-danfe-image",
        filename="danfe.jpg",
        mime_type="image/jpeg",
        sha256=__import__(
            "hashlib"
        ).sha256(
            b"fake-danfe-image"
        ).hexdigest(),
        metadata=metadata,
    )

    request = module.ExtractionRequest(
        document=document,
        requested_by="OP-K4B",
    )

    assert request.document is document
    assert request.requested_by == "OP-K4B"


def test_extraction_request_rejects_non_danfe_document():
    module = load_module()

    try:
        module.ExtractionRequest(
            document=object(),
            requested_by="OP-K4B",
        )
    except Exception as exc:
        assert isinstance(
            exc,
            module.ExtractionFailure,
        )
    else:
        raise AssertionError(
            "ExtractionRequest accepted a non-DanfeDocument."
        )


def test_extraction_request_requires_operator_identity():
    module = load_module()
    acquisition = load_acquisition_module()

    metadata = acquisition.DanfeAcquisitionMetadata(
        source="HTTP_UPLOAD",
        operator_id="OP-K4B",
        acquired_at="2026-09-18T09:00:00-03:00",
    )

    document = acquisition.DanfeDocument(
        content=b"fake-danfe-image",
        filename="danfe.jpg",
        mime_type="image/jpeg",
        sha256=__import__(
            "hashlib"
        ).sha256(
            b"fake-danfe-image"
        ).hexdigest(),
        metadata=metadata,
    )

    try:
        module.ExtractionRequest(
            document=document,
            requested_by="",
        )
    except Exception as exc:
        assert isinstance(
            exc,
            module.ExtractionFailure,
        )
    else:
        raise AssertionError(
            "ExtractionRequest accepted empty requested_by."
        )


def test_failure_code_is_provider_neutral():
    module = load_module()

    cls = module.ExtractionFailureCode

    values = {
        item.value
        for item in cls
    }

    assert {
        "INVALID_REQUEST",
        "UNSUPPORTED_DOCUMENT",
        "EXTRACTION_FAILED",
        "INVALID_RESULT",
    }.issubset(values)

    forbidden_tokens = (
        "OPENAI",
        "GEMINI",
        "GOOGLE",
        "TESSERACT",
        "ANTHROPIC",
        "AZURE",
        "AWS",
    )

    for value in values:
        upper = str(value).upper()

        assert not any(
            token in upper
            for token in forbidden_tokens
        )


def test_extraction_failure_is_explicit_domain_boundary_error():
    module = load_module()

    assert issubclass(
        module.ExtractionFailure,
        Exception,
    )

    failure = module.ExtractionFailure(
        module.ExtractionFailureCode.EXTRACTION_FAILED,
        "machine extraction failed",
    )

    assert failure.code == (
        module.ExtractionFailureCode.EXTRACTION_FAILED
    )

    assert (
        "machine extraction failed"
        in str(failure)
    )


def test_extractor_is_abstract_application_port():
    module = load_module()

    cls = module.DanfeInvoiceExtractor

    assert inspect.isclass(cls)
    assert inspect.isabstract(cls)


def test_extractor_exposes_single_extract_operation():
    module = load_module()

    cls = module.DanfeInvoiceExtractor

    assert hasattr(cls, "extract")

    signature = inspect.signature(
        cls.extract
    )

    parameters = list(
        signature.parameters
    )

    assert parameters == [
        "self",
        "request",
    ]


def test_extract_is_abstract():
    module = load_module()

    method = (
        module
        .DanfeInvoiceExtractor
        .extract
    )

    assert getattr(
        method,
        "__isabstractmethod__",
        False,
    ) is True


def test_extractor_contract_uses_canonical_result_type():
    module = load_module()
    acquisition = load_acquisition_module()

    class FakeExtractor(
        module.DanfeInvoiceExtractor
    ):
        def extract(
            self,
            request,
        ):
            field = (
                acquisition
                .ExtractedInvoiceField
            )

            line = (
                acquisition
                .ExtractedInvoiceLine(
                    supplier_product_code=field(
                        value="SUP-P001",
                        confidence=0.99,
                        requires_review=False,
                    ),
                    description=field(
                        value="ARROZ TIPO 1 5KG",
                        confidence=0.98,
                        requires_review=False,
                    ),
                    gtin=field(
                        value="7891234567890",
                        confidence=0.99,
                        requires_review=False,
                    ),
                    commercial_unit=field(
                        value="UN",
                        confidence=0.95,
                        requires_review=False,
                    ),
                    quantity=field(
                        value="10",
                        confidence=0.99,
                        requires_review=False,
                    ),
                    unit_price=field(
                        value="27.90",
                        confidence=0.99,
                        requires_review=False,
                    ),
                )
            )

            return (
                acquisition
                .InvoiceExtractionResult(
                    document_sha256=(
                        request.document.sha256
                    ),
                    invoice_number=field(
                        value="45891",
                        confidence=0.99,
                        requires_review=False,
                    ),
                    supplier_id=field(
                        value="SUP-001",
                        confidence=0.95,
                        requires_review=True,
                    ),
                    lines=(line,),
                    extractor="FAKE_TEST_EXTRACTOR",
                    requires_review=True,
                )
            )

    metadata = acquisition.DanfeAcquisitionMetadata(
        source="HTTP_UPLOAD",
        operator_id="OP-K4B",
        acquired_at="2026-09-18T09:00:00-03:00",
    )

    document = acquisition.DanfeDocument(
        content=b"fake-danfe-image",
        filename="danfe.jpg",
        mime_type="image/jpeg",
        sha256=__import__(
            "hashlib"
        ).sha256(
            b"fake-danfe-image"
        ).hexdigest(),
        metadata=metadata,
    )

    request = module.ExtractionRequest(
        document=document,
        requested_by="OP-K4B",
    )

    result = FakeExtractor().extract(
        request
    )

    assert isinstance(
        result,
        acquisition.InvoiceExtractionResult,
    )

    assert result.document_sha256 == (
        document.sha256
    )

    assert result.requires_review is True


def test_port_has_no_stock_or_receiving_authority():
    module = load_module()

    cls = module.DanfeInvoiceExtractor

    forbidden = (
        "receive_stock",
        "receive_goods",
        "add_stock",
        "create_batch",
        "putaway",
        "register_product",
        "register_new_product",
        "reconcile",
        "persist",
    )

    for name in forbidden:
        assert not hasattr(
            cls,
            name,
        )


def test_module_has_no_concrete_provider_exports():
    module = load_module()

    forbidden = (
        "OpenAIExtractor",
        "GeminiExtractor",
        "GoogleVisionExtractor",
        "TesseractExtractor",
        "AnthropicExtractor",
        "AzureExtractor",
        "AwsExtractor",
    )

    for name in forbidden:
        assert not hasattr(
            module,
            name,
        )
