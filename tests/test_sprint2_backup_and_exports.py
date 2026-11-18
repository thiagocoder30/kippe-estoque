import sqlite3
from pathlib import Path
import pytest
import app as gateway_app


@pytest.fixture
def sprint2_client():
    assert gateway_app.container.config.ENV == "testing"
    client = gateway_app.app.test_client()

    for attr_name in dir(gateway_app.container):
        repo_obj = getattr(gateway_app.container, attr_name, None)
        if hasattr(repo_obj, "_init_db") and callable(repo_obj._init_db):
            repo_obj._init_db()
    with gateway_app.container.operator_repository._get_connection() as conn:
        conn.execute("DELETE FROM operators")
        conn.commit()

    conn_main = sqlite3.connect(str(gateway_app.container.config.DB_PATH))
    try:
        conn_main.execute("DELETE FROM batches")
        conn_main.execute("DELETE FROM products")
        conn_main.execute("DELETE FROM operational_audit_events")
        conn_main.execute(
            """
            INSERT INTO products (id, name, ean, quantity, unit_of_measure, status, reserved_quantity)
            VALUES ('SKU-100', 'LEITE INTEGRAL 1L', '7890001112223', 48, 'un', 'ATIVO', 6)
            """
        )
        conn_main.execute(
            """
            INSERT INTO batches (
                product_id, batch_code, expiration_date, quantity,
                supplier, status, location_id, cost_per_unit
            ) VALUES ('SKU-100', 'LOTE-A1', '2026-11-25', 48, 'LATICINIOS SUL', 'ATIVO', 'A-01-01', 4.50)
            """
        )
        conn_main.execute(
            """
            INSERT INTO operational_audit_events (
                event_type, product_id, batch_code, location_id,
                quantity_planned, quantity_actual, quantity_divergence,
                supplier, document_id, operator_id
            ) VALUES ('RECEIVING_COMMIT', 'SKU-100', 'LOTE-A1', 'A-01-01', 50, 48, -2, 'LATICINIOS SUL', 'NF-5544', 'CONF-01')
            """
        )
        conn_main.commit()
    finally:
        conn_main.close()

    auth_uc = gateway_app.container.auth_use_case
    assert auth_uc.register("ADM-01", "Thiago Souza", "9999", "ADMIN_SISTEMA").is_success
    assert auth_uc.register("CONF-01", "Carlos Conferente", "1111", "CONFERENTE").is_success
    return client


def _login(client, op_id: str, pin: str):
    res = client.post("/api/auth/login", json={"id": op_id, "pin": pin})
    assert res.status_code == 200
    return res.get_json()["operator"]


def test_sqlite_backup_integrity_download_and_rbac(sprint2_client):
    client = sprint2_client

    # Conferente bloqueado (403)
    _login(client, "CONF-01", "1111")
    assert client.post("/api/admin/backup").status_code == 403
    client.post("/api/auth/logout")

    # Admin gera backup validado
    _login(client, "ADM-01", "9999")
    r_bk = client.post("/api/admin/backup")
    assert r_bk.status_code == 201
    body = r_bk.get_json()
    assert body["ok"] is True
    assert body["integrity"] == "ok"
    assert body["size_bytes"] > 0
    assert len(body["sha256"]) == 64
    assert body["download_folder_saved"] is False  # Isolado em testing

    # Download direto do arquivo .db gerado
    r_dl = client.get(body["download_url"])
    assert r_dl.status_code == 200
    assert r_dl.data.startswith(b"SQLite format 3\x00")
    r_dl.close()

    # Limpa artefato de teste em backups/
    (Path("backups") / body["filename"]).unlink(missing_ok=True)


def test_management_csv_exports_and_rbac(sprint2_client):
    client = sprint2_client

    # Conferente bloqueado (403)
    _login(client, "CONF-01", "1111")
    assert client.get("/api/reports/export/inventario.csv").status_code == 403
    client.post("/api/auth/logout")

    # Admin exporta os 3 relatórios gerenciais
    _login(client, "ADM-01", "9999")

    r_inv = client.get("/api/reports/export/inventario.csv")
    assert r_inv.status_code == 200
    txt_inv = r_inv.data.decode("utf-8-sig")
    assert "SKU;EAN;Produto;Categoria" in txt_inv
    assert "SKU-100;7890001112223;LEITE INTEGRAL 1L" in txt_inv

    r_fefo = client.get("/api/reports/export/fefo.csv")
    assert r_fefo.status_code == 200
    txt_fefo = r_fefo.data.decode("utf-8-sig")
    assert "SKU;Produto;EAN;Lote;Validade;Dias_Para_Vencer;Faixa_Risco" in txt_fefo
    assert "LOTE-A1;2026-11-25" in txt_fefo

    r_rec = client.get("/api/reports/export/recebimentos.csv")
    assert r_rec.status_code == 200
    txt_rec = r_rec.data.decode("utf-8-sig")
    assert "ID_Evento;Data_Hora;Tipo_Evento;SKU;Produto;Lote;Qtd_Prevista;Qtd_Conferida;Divergencia" in txt_rec
    assert "NF-5544" in txt_rec


def test_frontend_sprint2_contracts():
    app_js = Path("web/js/app.js").read_text()
    assert "openBackupAndExportModal" in app_js
    assert "/api/admin/backup" in app_js
    assert "/api/reports/export/" in app_js
