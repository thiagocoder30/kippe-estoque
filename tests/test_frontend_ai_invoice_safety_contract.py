from pathlib import Path


def test_ai_invoice_flow_does_not_contain_hardcoded_receiving_data():

    javascript = Path("web/js/app.js").read_text()

    forbidden = [
        '7891242151567',
        'NF-004992831',
        '2027-12-31',
        'DISTRIBUIDORA KIPPE',
        'ADMIN (IA)',
    ]

    for value in forbidden:
        assert value not in javascript


def test_ai_invoice_flow_does_not_submit_receiving_directly():

    javascript = Path("web/js/app.js").read_text()

    start = javascript.find(
        "const btnAi = document.getElementById('btn-inbound-ai');"
    )

    if start == -1:
        return

    end = javascript.find(
        "const submitReceive = document.getElementById('submit-receive');",
        start,
    )

    block = javascript[start:end]

    assert "registerReceive" not in block


def test_mock_ai_confirmation_control_is_not_exposed():

    html = Path("web/index.html").read_text()

    assert 'id="btn-confirm-ai-batch"' not in html


def test_ai_invoice_entry_is_explicitly_unavailable_until_real_extractor_exists():

    html = Path("web/index.html").read_text()

    assert 'id="btn-inbound-ai"' in html
    assert "EM DESENVOLVIMENTO" in html
