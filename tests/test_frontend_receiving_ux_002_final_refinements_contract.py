from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def input_fragment(html, element_id, radius=500):
    marker = f'id="{element_id}"'
    position = html.index(marker)

    start = max(
        0,
        position - radius,
    )

    end = min(
        len(html),
        position + radius,
    )

    return html[start:end]


def test_receiving_ean_requests_numeric_mobile_keyboard_without_numeric_storage():
    html = read("web/index.html")

    fragment = input_fragment(
        html,
        "rec-ean",
    )

    assert 'type="text"' in fragment
    assert 'inputmode="numeric"' in fragment
    assert 'type="number"' not in fragment


def test_assisted_putaway_exposes_receiving_specific_batch_semantics():
    html = read("web/index.html")
    javascript = read("web/js/app.js")

    assert 'id="putaway-batch-heading"' in html
    assert 'id="putaway-batch-description"' in html

    assert "LOTE DESTE RECEBIMENTO" in javascript
    assert (
        "Lote recém-recebido aguardando endereçamento."
        in javascript
    )

    assert "preferredBatchCode" in javascript


def test_manual_putaway_preserves_fefo_batch_semantics():
    javascript = read("web/js/app.js")

    assert "LOTE PRIORITÁRIO PENDENTE" in javascript
    assert (
        "Menor validade entre os lotes ainda não endereçados."
        in javascript
    )

    assert "pendingBatches" in javascript

    assert ".sort(" in javascript
    assert "expiration_date" in javascript


def test_product_search_name_wraps_instead_of_truncating():
    javascript = read(
        "web/js/product_search.js"
    )

    assert (
        "'text-sm font-black text-gray-800 "
        "whitespace-normal break-words leading-snug'"
        in javascript
    )

    assert (
        "'text-sm font-black text-gray-800 truncate'"
        not in javascript
    )


def test_product_search_ean_is_readable_without_ellipsis():
    javascript = read(
        "web/js/product_search.js"
    )

    assert (
        "'text-[9px] text-gray-400 font-mono "
        "mt-1 break-all'"
        in javascript
    )

    assert (
        "'text-[9px] text-gray-400 font-mono "
        "mt-1 truncate'"
        not in javascript
    )


def test_product_search_result_is_mobile_friendly():
    javascript = read(
        "web/js/product_search.js"
    )

    assert (
        "'justify-between items-start gap-3'"
        in javascript
    )

    assert "shrink-0" in javascript
    assert "self-start" in javascript


def test_product_search_keeps_canonical_behavior():
    javascript = read(
        "web/js/product_search.js"
    )

    assert "suggestProducts" in javascript
    assert "product.id" in javascript
    assert "this.button.click()" in javascript
    assert "/api/search" not in javascript
