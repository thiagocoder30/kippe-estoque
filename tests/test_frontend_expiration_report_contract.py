from pathlib import Path


def test_api_client_exposes_expiration_report_contract():

    javascript = Path("web/js/api.js").read_text()

    assert "async getExpirationReport()" in javascript
    assert "/api/relatorios/vencimentos" in javascript


def test_app_does_not_fetch_expiration_report_directly():

    javascript = Path("web/js/app.js").read_text()

    assert "fetch('/api/relatorios/vencimentos" not in javascript


def test_app_uses_api_client_for_expiration_report():

    javascript = Path("web/js/app.js").read_text()

    assert "this.api.getExpirationReport()" in javascript


def test_frontend_does_not_report_fake_server_crash():

    javascript = Path("web/js/app.js").read_text()

    assert "ERRO 500: SERVIDOR PYTHON CAIU" not in javascript
    assert "CRASH FRONTEND" not in javascript
    assert "FALHA DE COMUNICAÇÃO INTERNA" not in javascript
