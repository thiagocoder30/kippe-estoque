from pathlib import Path


def _receiving_product_loader() -> str:
    javascript = Path("web/js/app.js").read_text()

    start = javascript.index(
        "    async loadReceivingProduct(identifier)"
    )

    end = javascript.index(
        "    updateReceivingExpirationIntelligence()",
        start,
    )

    return javascript[start:end]


def test_receiving_form_exposes_visible_product_description():

    html = Path("web/index.html").read_text()

    assert 'id="rec-product-description"' in html
    assert "DESCRIÇÃO DO PRODUTO" in html


def test_receiving_product_description_is_not_operator_editable():

    html = Path("web/index.html").read_text()

    description_block = html.split(
        'id="rec-product-description"',
        1,
    )[1][:500]

    assert "readonly" in description_block


def test_receiving_product_description_starts_unidentified():

    html = Path("web/index.html").read_text()

    assert "AGUARDANDO IDENTIFICAÇÃO" in html


def test_receiving_query_populates_product_description():

    javascript = _receiving_product_loader()
    compact = "".join(javascript.split())

    assert "rec-product-description" in javascript
    assert "data.name" in javascript
    assert "descriptionInput.value=data.name;" in compact


def test_unknown_product_does_not_fabricate_description():

    javascript = _receiving_product_loader()
    compact = "".join(javascript.split())

    forbidden = [
        "PRODUTO PADRAO",
        "PRODUTO GENÉRICO",
        "SEM DESCRIÇÃO",
    ]

    for value in forbidden:
        assert value not in javascript

    assert "descriptionInput.value='';" in compact
