import io
import json
from pathlib import Path
from unittest.mock import patch
import app as gateway_app


def _login_admin(client):
    gateway_app.container.operator_repository._init_db()
    with gateway_app.container.operator_repository._get_connection() as conn:
        conn.execute("DELETE FROM operators")
        conn.commit()
    gateway_app.container.auth_use_case.register("ADM-01", "Admin", "9999", "ADMIN_SISTEMA")
    res = client.post("/api/auth/login", json={"id": "ADM-01", "pin": "9999"})
    assert res.status_code == 200


def test_upload_urls_returns_disabled_when_supabase_not_configured(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    client = gateway_app.app.test_client()
    _login_admin(client)

    res = client.post("/api/invoices/upload-urls", json={"files": [{"name": "nf.pdf", "type": "application/pdf"}]})
    assert res.status_code == 200
    assert res.get_json()["enabled"] is False


def test_storage_ocr_rejects_path_traversal_and_cleans_up_after_ocr(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://demo.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-secret-key")
    monkeypatch.setenv("SUPABASE_INVOICES_BUCKET", "invoices-tmp")
    client = gateway_app.app.test_client()
    _login_admin(client)

    # 1. Bloqueia path traversal
    bad_res = client.post(
        "/api/invoices/ocr",
        json={"storage_paths": [{"path": "../etc/passwd", "name": "passwd", "mime_type": "text/plain"}]},
    )
    assert bad_res.status_code == 400

    # 2. Fluxo válido baixa do Storage, roda OCR e apaga objeto temporário no finally
    class FakeResp:
        def __init__(self, raw: bytes):
            self._buf = io.BytesIO(raw)

        def read(self):
            return self._buf.read()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    captured_calls = []

    def fake_urlopen(req, timeout=15):
        captured_calls.append((req.get_method(), req.full_url))
        if req.get_method() == "GET":
            return FakeResp(b"%PDF-1.4 fake content")
        return FakeResp(b"{}")

    valid_path = "ocr/" + ("a" * 32) + "_nota.pdf"
    with patch("urllib.request.urlopen", side_effect=fake_urlopen), patch.object(
        gateway_app, "_ocr_response", return_value=({"items": [], "supplier": "TESTE"}, 200)
    ):
        ok_res = client.post(
            "/api/invoices/ocr",
            json={"storage_paths": [{"path": valid_path, "name": "nota.pdf", "mime_type": "application/pdf"}]},
        )
        assert ok_res.status_code == 200

    methods = [m for m, _ in captured_calls]
    assert "GET" in methods
    assert "DELETE" in methods


def test_frontend_storage_bypass_contract():
    conf_js = Path("web/js/features/conference.js").read_text()
    assert "/api/invoices/upload-urls" in conf_js
    assert "storage_paths" in conf_js
