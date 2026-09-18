"""
NF-001K.4C — Structured DANFE Extraction Orchestrator

RED contract.

The orchestrator is the application authority that executes one
provider-neutral DanfeInvoiceExtractor and validates the contextual
integrity of its result.

It MUST:

* accept only the canonical extraction port;
* execute exactly one extraction for one request;
* return a canonical InvoiceExtractionResult;
* preserve explicit ExtractionFailure values;
* translate unexpected provider exceptions into EXTRACTION_FAILED;
* reject non-canonical provider results as INVALID_RESULT;
* reject results bound to a different DANFE SHA-256;
* reject machine results that attempt to bypass human review.

It MUST NOT:

* know a concrete OCR/AI provider;
* perform HTTP requests;
* mutate stock;
* execute receiving;
* persist receiving mutations;
* reconcile products;
* register products;
* create ReviewedInvoiceExtraction automatically.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect


MODULE_NAME = (
    "src.application.procurement."
    "danfe_extraction_orchestrator"
)

PORT_MODULE_NAME = (
    "src.application.procurement."
    "danfe_extraction"
)

ACQUISITION_MODULE_NAME = (
    "src.application.procurement."
    "danfe_acquisition"
)


def load_module():
    return importlib.import_module(MODULE_NAME)


def load_port():
    return importlib.import_module(PORT_MODULE_NAME)


def load_acquisition():
    return importlib.import_module(
        ACQUISITION_MODULE_NAME
    )


def make_document():
    acquisition = load_acquisition()

    content = b"nf-001k-4c-danfe-image"

    metadata = acquisition.DanfeAcquisitionMetadata(
        source="HTTP_UPLOAD",
        operator_id="OP-K4C",
        acquired_at="2026-09-18T10:00:00-03:00",
    )

    return acquisition.DanfeDocument(
        content=content,
        filename="danfe-k4c.jpg",
        mime_type="image/jpeg",
        sha256=hashlib.sha256(content).hexdigest(),
        metadata=metadata,
    )


def make_request():
    port = load_port()

    return port.ExtractionRequest(
        document=make_document(),
        requested_by="OP-K4C",
    )


def make_result(
    request,
    *,
    document_sha256=None,
    requires_review=True,
):
    acquisition = load_acquisition()

    field = acquisition.ExtractedInvoiceField

    line = acquisition.ExtractedInvoiceLine(
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
            confidence=0.97,
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

    return acquisition.InvoiceExtractionResult(
        document_sha256=(
            document_sha256
            if document_sha256 is not None
            else request.document.sha256
        ),
        invoice_number=field(
            value="45891",
            confidence=0.99,
            requires_review=False,
        ),
        supplier_id=field(
            value="SUP-001",
            confidence=0.96,
            requires_review=False,
        ),
        lines=(line,),
        extractor="FAKE_K4C_EXTRACTOR",
        requires_review=requires_review,
    )


class SuccessfulExtractor(
    load_port().DanfeInvoiceExtractor
):
    def __init__(self):
        self.calls = []

    def extract(self, request):
        self.calls.append(request)
        return make_result(request)


def test_orchestrator_module_exists():
    module = load_module()
    assert module is not None


def test_orchestrator_exports_required_contract():
    module = load_module()

    assert hasattr(
        module,
        "DanfeExtractionOrchestrator",
    )


def test_orchestrator_has_single_extraction_dependency():
    module = load_module()

    signature = inspect.signature(
        module.DanfeExtractionOrchestrator
    )

    assert list(signature.parameters) == [
        "extractor",
    ]


def test_orchestrator_rejects_non_extractor_dependency():
    module = load_module()
    port = load_port()

    try:
        module.DanfeExtractionOrchestrator(
            extractor=object(),
        )
    except port.ExtractionFailure as exc:
        assert exc.code == (
            port.ExtractionFailureCode.INVALID_REQUEST
        )
        return

    raise AssertionError(
        "Orchestrator accepted an invalid extractor."
    )


def test_orchestrator_executes_exactly_one_extraction():
    module = load_module()

    extractor = SuccessfulExtractor()

    orchestrator = (
        module.DanfeExtractionOrchestrator(
            extractor=extractor,
        )
    )

    request = make_request()

    result = orchestrator.extract(request)

    assert len(extractor.calls) == 1
    assert extractor.calls[0] is request
    assert result.document_sha256 == (
        request.document.sha256
    )


def test_orchestrator_rejects_invalid_request():
    module = load_module()
    port = load_port()

    class Extractor(port.DanfeInvoiceExtractor):
        def extract(self, request):
            raise AssertionError(
                "provider must not be called"
            )

    orchestrator = (
        module.DanfeExtractionOrchestrator(
            extractor=Extractor(),
        )
    )

    try:
        orchestrator.extract(object())
    except port.ExtractionFailure as exc:
        assert exc.code == (
            port.ExtractionFailureCode.INVALID_REQUEST
        )
        return

    raise AssertionError(
        "Orchestrator accepted invalid request."
    )


def test_orchestrator_preserves_explicit_extraction_failure():
    module = load_module()
    port = load_port()

    failure = port.ExtractionFailure(
        port.ExtractionFailureCode.UNSUPPORTED_DOCUMENT,
        "unsupported DANFE",
    )

    class Extractor(port.DanfeInvoiceExtractor):
        def extract(self, request):
            raise failure

    orchestrator = (
        module.DanfeExtractionOrchestrator(
            extractor=Extractor(),
        )
    )

    try:
        orchestrator.extract(make_request())
    except port.ExtractionFailure as exc:
        assert exc is failure
        return

    raise AssertionError(
        "Explicit ExtractionFailure was not preserved."
    )


def test_orchestrator_translates_unexpected_provider_exception():
    module = load_module()
    port = load_port()

    class Extractor(port.DanfeInvoiceExtractor):
        def extract(self, request):
            raise RuntimeError(
                "provider-specific failure"
            )

    orchestrator = (
        module.DanfeExtractionOrchestrator(
            extractor=Extractor(),
        )
    )

    try:
        orchestrator.extract(make_request())
    except port.ExtractionFailure as exc:
        assert exc.code == (
            port.ExtractionFailureCode.EXTRACTION_FAILED
        )

        assert (
            "provider-specific failure"
            not in str(exc)
        )

        return

    raise AssertionError(
        "Unexpected provider exception leaked."
    )


def test_orchestrator_rejects_non_canonical_result():
    module = load_module()
    port = load_port()

    class Extractor(port.DanfeInvoiceExtractor):
        def extract(self, request):
            return {
                "invoice_number": "45891",
            }

    orchestrator = (
        module.DanfeExtractionOrchestrator(
            extractor=Extractor(),
        )
    )

    try:
        orchestrator.extract(make_request())
    except port.ExtractionFailure as exc:
        assert exc.code == (
            port.ExtractionFailureCode.INVALID_RESULT
        )
        return

    raise AssertionError(
        "Non-canonical extraction result accepted."
    )


def test_orchestrator_rejects_result_for_different_document():
    module = load_module()
    port = load_port()

    class Extractor(port.DanfeInvoiceExtractor):
        def extract(self, request):
            return make_result(
                request,
                document_sha256="f" * 64,
            )

    orchestrator = (
        module.DanfeExtractionOrchestrator(
            extractor=Extractor(),
        )
    )

    try:
        orchestrator.extract(make_request())
    except port.ExtractionFailure as exc:
        assert exc.code == (
            port.ExtractionFailureCode.INVALID_RESULT
        )
        return

    raise AssertionError(
        "Result for another DANFE was accepted."
    )


def test_orchestrator_requires_human_review_boundary():
    module = load_module()
    port = load_port()

    class Extractor(port.DanfeInvoiceExtractor):
        def extract(self, request):
            return make_result(
                request,
                requires_review=False,
            )

    orchestrator = (
        module.DanfeExtractionOrchestrator(
            extractor=Extractor(),
        )
    )

    try:
        orchestrator.extract(make_request())
    except port.ExtractionFailure as exc:
        assert exc.code == (
            port.ExtractionFailureCode.INVALID_RESULT
        )
        return

    raise AssertionError(
        "Machine extraction bypassed human review."
    )


def test_orchestrator_returns_same_valid_canonical_result():
    module = load_module()
    port = load_port()

    class Extractor(port.DanfeInvoiceExtractor):
        def __init__(self):
            self.result = None

        def extract(self, request):
            self.result = make_result(request)
            return self.result

    extractor = Extractor()

    orchestrator = (
        module.DanfeExtractionOrchestrator(
            extractor=extractor,
        )
    )

    result = orchestrator.extract(
        make_request()
    )

    assert result is extractor.result


def test_orchestrator_does_not_create_human_review():
    module = load_module()

    forbidden = (
        "review",
        "approve",
        "accept",
        "confirm",
        "receive",
        "persist",
        "reconcile",
        "register_product",
        "mutate_stock",
    )

    cls = module.DanfeExtractionOrchestrator

    for name in forbidden:
        assert not hasattr(cls, name)


def test_module_has_no_concrete_provider_or_transport_dependency():
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
        "google.cloud",
        "pytesseract",
        "import cv2",
        "from cv2",
        "requests.",
        "httpx.",
        "urllib.",
    )

    for marker in forbidden:
        assert marker not in source


def test_module_has_no_receiving_or_stock_authority():
    module = load_module()

    source = open(
        module.__file__,
        "r",
        encoding="utf-8",
    ).read().lower()

    forbidden = (
        "receiving_execution",
        "receiving_persistence",
        "operator_receiving_integration",
        "sqlite_repository",
        "stock_repository",
        "inventory_repository",
    )

    for marker in forbidden:
        assert marker not in source
