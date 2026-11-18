import sqlite3
from pathlib import Path
import pytest
import app as gateway_app


@pytest.fixture
def sprint3_client():
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
        conn_extra.execute("DELETE FROM conference_audit_log")
        conn_extra.execute("DELETE FROM receiving_pending_queue")
        conn_extra.execute("DELETE FROM receiving_divergences")
        conn_extra.commit()
    finally:
        conn_extra.close()

    conn_main = sqlite3.connect(str(gateway_app.container.config.DB_PATH))
    try:
        conn_main.execute("DELETE FROM batches")
        conn_main.execute("DELETE FROM products")
        conn_main.execute(
            """
            INSERT INTO products (id, name, ean, quantity, unit_of_measure, status, reserved_quantity)
            VALUES ('SKU-500', 'OLEO DE SOJA 900ML', '7895556667778', 0, 'un', 'ATIVO', 0)
            """
        )
        conn_main.commit()
    finally:
        conn_main.close()

    auth_uc = gateway_app.container.auth_use_case
    assert auth_uc.register("ADM-01", "Thiago Souza", "9999", "ADMIN_SISTEMA").is_success
    assert auth_uc.register("CONF-01", "Carlos Conferente", "1111", "CONFERENTE").is_success
    assert auth_uc.register("EST-01", "Maria Estoquista", "2222", "ESTOQUISTA").is_success
    return client


def _login(client, op_id: str, pin: str):
    res = client.post("/api/auth/login", json={"id": op_id, "pin": pin})
    assert res.status_code == 200
    return res.get_json()["operator"]


def test_multinf_romaneio_allocation_duplicate_lock_and_divergence_csv(sprint3_client):
    client = sprint3_client

    # 1. Conferente recebe 2 NFs do mesmo fornecedor (NF-101 com 10 un + NF-102 com 15 un = 25 un faturadas),
    #    mas conta fisicamente apenas 22 un na doca (divergência -3 un) e formaliza motivo.
    _login(client, "CONF-01", "1111")
    payload_romaneio = {
        "supplier": "BUNGE ALIMENTOS",
        "invoice_number": "101, 102",
        "invoices": ["101", "102"],
        "items": [
            {
                "sku": "SKU-500",
                "quantity": 22,
                "batch_code": "L-2026A",
                "expiration_date": "2027-06-30",
                "nf_allocations": [
                    {"invoice_number": "101", "nf_qty": 10, "expected_units": 10},
                    {"invoice_number": "102", "nf_qty": 15, "expected_units": 15},
                ],
            }
        ],
        "divergences": [
            {
                "sku": "SKU-500",
                "name": "OLEO DE SOJA 900ML",
                "invoice_number": "101, 102",
                "expected_qty": 25,
                "counted_qty": 22,
                "reason": "FALTA_TRANSPORTE",
                "notes": "Faltaram 3 unidades na NF 102",
            }
        ],
    }

    r_sub = client.post("/api/conference/finalize", json=payload_romaneio)
    assert r_sub.status_code == 202
    q_data = r_sub.get_json()
    assert q_data["queued"] is True
    assert q_data["submitted_items"] == 2  # Rateado em NF 101 (10 un) + NF 102 (12 un)
    assert q_data["divergences_recorded"] == 1
    queue_id = q_data["queue_id"]

    # 2. Trava de duplicidade bloqueia tentativa de reenviar a NF 101 enquanto pendente
    r_dup_pending = client.post(
        "/api/conference/finalize",
        json={
            "supplier": "BUNGE ALIMENTOS",
            "invoice_number": "101",
            "invoices": ["101"],
            "items": [{"sku": "SKU-500", "quantity": 10, "expiration_date": "2027-06-30"}],
        },
    )
    assert r_dup_pending.status_code == 409
    assert r_dup_pending.get_json()["duplicate"] is True
    client.post("/api/auth/logout")

    # 3. Estoquista aprova o romaneio rateado e efetiva 22 un no estoque
    _login(client, "EST-01", "2222")
    r_app = client.post(f"/api/receiving/pending/{queue_id}/approve", json={})
    assert r_app.status_code == 200
    res_list = r_app.get_json()["results"]
    assert len(res_list) == 2
    assert res_list[0]["invoice_number"] == "101"
    assert res_list[0]["quantity"] == 10
    assert res_list[1]["invoice_number"] == "102"
    assert res_list[1]["quantity"] == 12
    client.post("/api/auth/logout")

    # 4. Admin verifica trava pós-efetivação e exporta CSV de divergências
    _login(client, "ADM-01", "9999")
    r_chk = client.post(
        "/api/invoices/check-duplicate",
        json={"supplier": "BUNGE ALIMENTOS", "invoice_number": "102"},
    )
    assert r_chk.status_code == 200
    assert r_chk.get_json()["duplicate"] is True

    r_csv = client.get("/api/reports/export/divergencias.csv")
    assert r_csv.status_code == 200
    csv_txt = r_csv.data.decode("utf-8-sig")
    assert "FALTA_TRANSPORTE" in csv_txt
    assert "Faltaram 3 unidades na NF 102" in csv_txt


def test_frontend_sprint3_contracts():
    conf_js = Path("web/js/features/conference.js").read_text()
    assert "renderAttachedInvoicesBanner" in conf_js
    assert "promptDivergenceFormalization" in conf_js
    assert "/api/invoices/check-duplicate" in conf_js
    assert "nf_allocations" in conf_js
