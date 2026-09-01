from pathlib import Path


def api_javascript():
    return Path("web/js/api.js").read_text(encoding="utf-8")


def app_javascript():
    return Path("web/js/app.js").read_text(encoding="utf-8")


def index_html():
    return Path("web/index.html").read_text(encoding="utf-8")


def test_api_client_exposes_login():
    javascript = api_javascript()

    assert "async login(" in javascript
    assert "/api/auth/login" in javascript


def test_api_client_exposes_current_session():
    javascript = api_javascript()

    assert "async getCurrentOperator(" in javascript
    assert "/api/auth/me" in javascript


def test_api_client_exposes_logout():
    javascript = api_javascript()

    assert "async logout(" in javascript
    assert "/api/auth/logout" in javascript


def test_api_requests_preserve_browser_session_credentials():
    javascript = api_javascript()

    assert "credentials: 'same-origin'" in javascript


def test_application_tracks_authenticated_operator():
    javascript = app_javascript()

    assert "this.currentOperator" in javascript


def test_bootstrap_restores_existing_session():
    javascript = app_javascript()

    assert "restoreOperatorSession" in javascript
    assert "await this.restoreOperatorSession()" in javascript


def test_application_exposes_login_flow():
    javascript = app_javascript()

    assert "bindAuthentication" in javascript
    assert "authenticateOperator" in javascript


def test_application_exposes_logout_flow():
    javascript = app_javascript()

    assert "logoutOperator" in javascript


def test_application_updates_operator_identity_from_session():
    javascript = app_javascript()

    assert "renderOperatorIdentity" in javascript
    assert "operator.name" in javascript
    assert "operator.role" in javascript


def test_login_modal_exists():
    html = index_html()

    assert 'id="auth-modal"' in html
    assert 'id="auth-operator-id"' in html
    assert 'id="auth-pin"' in html
    assert 'id="auth-submit"' in html


def test_login_modal_is_blocking_until_authenticated():
    html = index_html()

    assert "IDENTIFICAÇÃO DO OPERADOR" in html
    assert "ENTRAR NO WMS" in html


def test_header_operator_identity_is_dynamic():
    html = index_html()

    assert 'id="header-operator-name"' in html
    assert 'id="home-operator-name"' in html
    assert 'id="home-operator-role"' in html


def test_logout_control_exists():
    html = index_html()

    assert 'id="operator-logout-btn"' in html


def test_fake_admin_greeting_is_removed():
    html = index_html()

    assert "Olá, ADMIN" not in html


def test_fake_static_admin_header_is_removed():
    html = index_html()

    assert ">ADMIN</button>" not in html


def test_auth_error_has_visible_target():
    html = index_html()

    assert 'id="auth-error"' in html


def test_existing_receiving_flow_is_preserved():
    javascript = app_javascript()

    assert "this.api.registerReceive" in javascript
    assert "submit-receive" in javascript


def test_existing_scanner_integration_is_preserved():
    javascript = app_javascript()

    assert "ScannerManager" in javascript
    assert "this.scanner.start()" in javascript
