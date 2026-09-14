from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "web" / "index.html"


def html():
    return HTML.read_text(encoding="utf-8")


def element_by_id(source: str, element_id: str) -> str:
    """
    Returns the opening element carrying the requested id.
    This deliberately checks structural ownership instead of
    merely searching for words somewhere in the document.
    """
    pattern = re.compile(
        rf"<(?P<tag>[a-zA-Z0-9]+)\b"
        rf"(?P<attrs>[^>]*\bid=[\"']{re.escape(element_id)}[\"'][^>]*)>",
        re.IGNORECASE | re.DOTALL,
    )

    match = pattern.search(source)

    assert match is not None, (
        f"element with id={element_id!r} was not found"
    )

    return match.group(0)


def text_element_by_id(source: str, element_id: str) -> str:
    """
    Returns the complete text-bearing element identified by id.
    """
    opening = element_by_id(source, element_id)

    tag_match = re.match(
        r"<([a-zA-Z0-9]+)\b",
        opening,
    )

    assert tag_match is not None

    tag = tag_match.group(1)

    start = source.index(opening)
    end_marker = f"</{tag}>"
    end = source.find(end_marker, start)

    assert end != -1, (
        f"closing tag for id={element_id!r} was not found"
    )

    return source[start:end + len(end_marker)]


def normalized_text(fragment: str) -> str:
    fragment = re.sub(
        r"<[^>]+>",
        " ",
        fragment,
    )
    return " ".join(fragment.split()).upper()


def test_post_create_has_two_explicit_business_decisions():
    source = html()

    assert 'id="continue-new-product-receiving"' in source
    assert 'id="continue-new-product-existing-stock"' in source

    assert "RECEBER MERCADORIA" in source
    assert "CADASTRAR ESTOQUE JÁ EXISTENTE" in source


def test_receiving_explanation_is_structurally_owned_by_receiving_decision():
    source = html()

    receiving_button_pos = source.index(
        'id="continue-new-product-receiving"'
    )

    receiving_explanation_pos = source.index(
        'id="new-product-receiving-explanation"'
    )

    existing_button_pos = source.index(
        'id="continue-new-product-existing-stock"'
    )

    assert (
        receiving_button_pos
        < receiving_explanation_pos
        < existing_button_pos
    ), (
        "the receiving explanation must appear immediately in the "
        "receiving decision region, before the existing-stock CTA"
    )


def test_existing_stock_explanation_is_structurally_owned_by_existing_stock_decision():
    source = html()

    existing_button_pos = source.index(
        'id="continue-new-product-existing-stock"'
    )

    existing_explanation_pos = source.index(
        'id="new-product-existing-stock-explanation"'
    )

    assert existing_button_pos < existing_explanation_pos


def test_receiving_explanation_describes_arrival_now_not_preexisting_stock():
    source = html()

    fragment = text_element_by_id(
        source,
        "new-product-receiving-explanation",
    )

    text = normalized_text(fragment)

    assert (
        "CHEGANDO AGORA" in text
        or "CHEGA AGORA" in text
        or "NOVA CHEGADA" in text
    ), (
        "receiving explanation must explicitly describe merchandise "
        "arriving now"
    )

    forbidden = (
        "JÁ ESTAVA FISICAMENTE NO ESTOQUE",
        "ESTOQUE PREEXISTENTE",
        "ESTOQUE JÁ EXISTENTE",
        "ANTES DE SER CONTROLADO PELO KIPPE",
    )

    for marker in forbidden:
        assert marker not in text, (
            "receiving explanation contains existing-stock semantics: "
            + marker
        )


def test_existing_stock_explanation_describes_preexisting_physical_stock():
    source = html()

    fragment = text_element_by_id(
        source,
        "new-product-existing-stock-explanation",
    )

    text = normalized_text(fragment)

    assert (
        "JÁ ESTAVA FISICAMENTE NO ESTOQUE" in text
        or "ESTOQUE PREEXISTENTE" in text
        or "ESTOQUE JÁ EXISTENTE" in text
    ), (
        "existing-stock explanation must explicitly describe stock "
        "that already physically existed"
    )


def test_existing_stock_explanation_does_not_describe_new_arrival():
    source = html()

    fragment = text_element_by_id(
        source,
        "new-product-existing-stock-explanation",
    )

    text = normalized_text(fragment)

    forbidden = (
        "ESTÁ CHEGANDO AGORA",
        "CHEGA AGORA",
        "NOVO RECEBIMENTO",
        "NOVA CHEGADA",
    )

    for marker in forbidden:
        assert marker not in text, (
            "existing-stock explanation contains receiving semantics: "
            + marker
        )


def test_receiving_accessibility_contract_remains_compatible():
    source = html()

    button = element_by_id(
        source,
        "continue-new-product-receiving",
    )

    assert "CONTINUAR RECEBIMENTO" in button.upper()


def test_visible_receiving_cta_remains_receive_merchandise():
    source = html()

    start = source.index(
        'id="continue-new-product-receiving"'
    )

    end = source.find(
        "</button>",
        start,
    )

    assert end != -1

    fragment = source[start:end]

    assert "RECEBER MERCADORIA" in fragment


def test_existing_stock_card_action_keeps_history_button_geometry():
    source = html()

    history = element_by_id(
        source,
        "btn-product-audit-history",
    )

    onboarding = element_by_id(
        source,
        "btn-existing-stock-onboarding",
    )

    geometry = (
        "w-full",
        "px-3",
        "py-2.5",
        "text-[10px]",
        "font-black",
        "tracking-wider",
        "active:scale-[0.98]",
    )

    for token in geometry:
        assert token in history, (
            f"history button missing geometry token {token}"
        )
        assert token in onboarding, (
            f"existing-stock button missing geometry token {token}"
        )


def test_business_decision_is_not_implemented_as_checkbox():
    source = html()

    modal_start = source.index(
        'id="new-product-success-modal"'
    )

    modal_end = source.find(
        "</div>",
        modal_start,
    )

    region = source[
        modal_start:
        modal_start + 12000
    ].lower()

    assert 'type="checkbox"' not in region


def test_receiving_and_existing_stock_use_distinct_visual_semantics():
    source = html()

    receiving = element_by_id(
        source,
        "continue-new-product-receiving",
    )

    existing = element_by_id(
        source,
        "continue-new-product-existing-stock",
    )

    assert (
        "bg-[#124191]" in receiving
        or "bg-blue" in receiving
    )

    assert (
        "bg-amber" in existing
        or "bg-orange" in existing
    )


def test_semantic_explanations_are_independently_addressable():
    source = html()

    assert source.count(
        'id="new-product-receiving-explanation"'
    ) == 1

    assert source.count(
        'id="new-product-existing-stock-explanation"'
    ) == 1
