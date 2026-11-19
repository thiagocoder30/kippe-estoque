from pathlib import Path
import pytest
import app as gateway_app


@pytest.fixture
def sprint1_client():
    assert gateway_app.container.config.ENV == "testing"
    client = gateway_app.app.test_client()

    for attr_name in dir(gateway_app.container):
        repo_obj = getattr(gateway_app.container, attr_name, None)
        if hasattr(repo_obj, "_init_db") and callable(repo_obj._init_db):
            repo_obj._init_db()
    with gateway_app.container.operator_repository._get_connection() as conn:
        conn.execute("DELETE FROM operators")
        conn.commit()

    conn_extra = gateway_app._get_kippe_db()
    try:
        conn_extra.execute("DELETE FROM institutional_audit_log")
        conn_extra.commit()
    finally:
        conn_extra.close()

    auth_uc = gateway_app.container.auth_use_case
    assert auth_uc.register("ADM-01", "Thiago Souza", "9999", "ADMIN_SISTEMA").is_success
    assert auth_uc.register("CONF-01", "Carlos Conferente", "1111", "CONFERENTE").is_success
    return client


def _login(client, op_id: str, pin: str):
    res = client.post("/api/auth/login", json={"id": op_id, "pin": pin})
    assert res.status_code == 200
    return res.get_json()["operator"]


def test_admin_reset_pin_and_operator_change_own_pin(sprint1_client):
    client = sprint1_client

    # Conferente não pode resetar PIN de terceiros (403)
    _login(client, "CONF-01", "1111")
    r_forbidden = client.patch("/api/operators/ADM-01/pin", json={"pin": "0000"})
    assert r_forbidden.status_code == 403
    client.post("/api/auth/logout")

    # Admin redefine PIN do Conferente para 5678
    _login(client, "ADM-01", "9999")
    r_reset = client.patch("/api/operators/CONF-01/pin", json={"pin": "5678"})
    assert r_reset.status_code == 200
    client.post("/api/auth/logout")

    # PIN antigo (1111) falha; novo PIN (5678) autentica
    assert client.post("/api/auth/login", json={"id": "CONF-01", "pin": "1111"}).status_code == 401
    _login(client, "CONF-01", "5678")

    # Conferente tenta trocar próprio PIN com senha atual errada -> 400
    r_bad_cur = client.post("/api/auth/change-pin", json={"current_pin": "9999", "new_pin": "2468"})
    assert r_bad_cur.status_code == 400

    # Conferente troca próprio PIN para 2468 com sucesso
    r_change = client.post("/api/auth/change-pin", json={"current_pin": "5678", "new_pin": "2468"})
    assert r_change.status_code == 200
    client.post("/api/auth/logout")

    # Valida login com PIN escolhido pelo próprio colaborador
    _login(client, "CONF-01", "2468")


def test_institutional_audit_trail_captures_and_filters_events(sprint1_client):
    client = sprint1_client

    # Conferente bloqueado de ler logs de auditoria (403)
    _login(client, "CONF-01", "1111")
    assert client.get("/api/audit/logs").status_code == 403
    client.post("/api/auth/logout")

    # Admin executa ações de governança e catálogo
    _login(client, "ADM-01", "9999")
    r_op = client.post(
        "/api/operators",
        json={"id": "EST-09", "name": "MARIA ESTOQUISTA", "pin": "3333", "role": "ESTOQUISTA"},
    )
    assert r_op.status_code == 201

    r_prod = client.post(
        "/api/produto",
        json={"name": "CAFE TORRADO 500G", "ean": "7891112223334"},
    )
    assert r_prod.status_code == 201

    # Consulta auditoria geral
    r_all = client.get("/api/audit/logs")
    assert r_all.status_code == 200
    body_all = r_all.get_json()
    assert body_all["total"] >= 4
    types = [e["event_type"] for e in body_all["logs"]]
    assert "OPERATOR_CREATED" in types
    assert "PRODUCT_CREATED" in types
    assert "AUTH_LOGIN" in types

    # Filtro por categoria GOVERNANCA e busca textual
    r_gov = client.get("/api/audit/logs?category=GOVERNANCA&q=MARIA")
    assert r_gov.status_code == 200
    gov_logs = r_gov.get_json()["logs"]
    assert len(gov_logs) == 1
    assert gov_logs[0]["target_ref"] == "EST-09"


def test_frontend_sprint1_contracts():
    app_js = Path("web/js/app.js").read_text()
    assert "openAuditLogsModal" in app_js
    assert "openChangeOwnPinModal" in app_js
    assert "/api/audit/logs" in app_js
    assert "/api/auth/change-pin" in app_js
