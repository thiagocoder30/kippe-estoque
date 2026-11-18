import os
import sqlite3
from pathlib import Path

import pytest

import app as gateway_app
from src.domain.access_control import AccessControl


@pytest.fixture
def isolated_gateway():
    """
    Garante ambiente de teste isolado (KIPPE_ENV=testing), limpa tabelas de fila/auditoria
    e registra 3 operadores distintos:
      - CONF-01: CONFERENTE
      - EST-01:  ESTOQUISTA
      - ADM-01:  ADMIN_SISTEMA (Thiago Souza)
    """
    assert gateway_app.container.config.ENV == "testing"
    client = gateway_app.app.test_client()

    gateway_app.container.operator_repository._init_db()
    gateway_app.container.product_repository._init_db()

    with gateway_app.container.operator_repository._get_connection() as conn:
        conn.execute("DELETE FROM operators")
        conn.commit()

    with gateway_app.container.product_repository._get_connection() as conn:
        conn.execute("DELETE FROM products")
        conn.commit()

    conn_extra = gateway_app._get_kippe_db()
    try:
        conn_extra.execute("DELETE FROM receiving_pending_queue")
        conn_extra.execute("DELETE FROM product_registration_requests")
        conn_extra.execute("DELETE FROM conference_audit_log")
        conn_extra.execute("DELETE FROM sku_aliases")
        conn_extra.execute("DELETE FROM sku_pack_defaults")
        conn_extra.commit()
    finally:
        conn_extra.close()

    auth_uc = gateway_app.container.auth_use_case
    assert auth_uc.register("CONF-01", "Carlos Conferente", "1111", "CONFERENTE").is_success
    assert auth_uc.register("EST-01", "Marcos Estoquista", "2222", "ESTOQUISTA").is_success
    assert auth_uc.register("ADM-01", "Thiago Souza", "9999", "ADMIN_SISTEMA").is_success

    return client


def _login(client, op_id: str, pin: str):
    res = client.post("/api/auth/login", json={"id": op_id, "pin": pin})
    assert res.status_code == 200, f"Falha no login de {op_id}: {res.get_json()}"
    return res.get_json()["operator"]


# ------------------------------------------------------------------
# 1. CONTRATO DE DOMÍNIO (RBAC)
# ------------------------------------------------------------------
def test_domain_access_control_matrix():
    assert AccessControl.is_valid_human_role("CONFERENTE") is True
    assert AccessControl.is_valid_human_role("ESTOQUISTA") is True
    assert AccessControl.is_valid_human_role("ADMIN_SISTEMA") is True
    assert AccessControl.is_valid_human_role("OPERADOR") is True

    # Conferente e Operador são restritos à conferência
    assert AccessControl.is_conference_only("CONFERENTE") is True
    assert AccessControl.is_conference_only("OPERADOR") is True
    assert AccessControl.can_manage_operational_catalog("CONFERENTE") is False
    assert AccessControl.can_approve_receiving("CONFERENTE") is False

    # Estoquista e Admin Sistema possuem privilégios de catálogo e armazenagem
    assert AccessControl.is_conference_only("ESTOQUISTA") is False
    assert AccessControl.can_manage_operational_catalog("ESTOQUISTA") is True
    assert AccessControl.can_approve_receiving("ESTOQUISTA") is True

    assert AccessControl.is_conference_only("ADMIN_SISTEMA") is False
    assert AccessControl.can_manage_operational_catalog("ADMIN_SISTEMA") is True
    assert AccessControl.can_approve_receiving("ADMIN_SISTEMA") is True
    assert AccessControl.is_system_admin("ADMIN_SISTEMA") is True


# ------------------------------------------------------------------
# 2. BLOQUEIO RÍGIDO DE CADASTRO DE PRODUTO PARA CONFERENTE
# ------------------------------------------------------------------
def test_conferente_blocked_from_creating_products_http(isolated_gateway):
    client = isolated_gateway
    op = _login(client, "CONF-01", "1111")
    assert op["role"] == "CONFERENTE"

    # Tentativa 1: Cadastro canônico (auto-SKU)
    res_auto = client.post(
        "/api/produto",
        json={"name": "PRODUTO PROIBIDO CONFERENTE", "ean": "7890000000111"},
    )
    assert res_auto.status_code == 403
    assert "Autorização negada" in res_auto.get_json()["error"]

    # Tentativa 2: Cadastro com SKU explícito
    res_explicit = client.post(
        "/api/produto",
        json={"id": "SKU-ILEGAL-99", "name": "PRODUTO EXPLICITO", "ean": "7890000000222"},
    )
    assert res_explicit.status_code == 403
    assert gateway_app.container.product_repository.get_by_id("SKU-ILEGAL-99") is None


# ------------------------------------------------------------------
# 3. ACESSO TOTAL PRESERVADO PARA ADMIN_SISTEMA (THIAGO SOUZA)
# ------------------------------------------------------------------
def test_admin_sistema_retains_full_unrestricted_access(isolated_gateway):
    client = isolated_gateway
    op = _login(client, "ADM-01", "9999")
    assert op["role"] == "ADMIN_SISTEMA"

    # 1. Admin cria produto diretamente
    res_prod = client.post(
        "/api/produto",
        json={"name": "BOMBOM GAROTO SORTIDOS 220G CX", "ean": "7891000457092"},
    )
    assert res_prod.status_code == 201
    sku = res_prod.get_json()["product"]["id"]

    # 2. Admin cria categoria (privilégio exclusivo ADMIN_SISTEMA)
    cat_post_routes = [
        rule.rule for rule in gateway_app.app.url_map.iter_rules()
        if "POST" in rule.methods and "categor" in rule.rule
    ]
    assert cat_post_routes, "Nenhuma rota POST de categoria encontrada"
    res_cat = client.post(
        cat_post_routes[0],
        json={"id": "CAT-MERCEARIA", "name": "MERCEARIA DOCE"},
    )
    assert res_cat.status_code in (200, 201)

    # 3. Admin finaliza conferência diretamente no estoque (200 OK, sem precisar fila)
    res_fin = client.post(
        "/api/conference/finalize",
        json={
            "supplier": "ATACADAO S.A.",
            "invoice_number": "460935",
            "items": [{"sku": sku, "quantity": 90, "batch_code": "L626212942G", "expiration_date": "2027-05-10"}],
        },
    )
    assert res_fin.status_code == 200
    body = res_fin.get_json()
    assert body.get("queued") is not True
    assert body["success"] == 1

    prod = gateway_app.container.product_repository.get_by_id(sku)
    assert prod.quantity == 90


# ------------------------------------------------------------------
# 4. SOLICITAÇÃO DE CADASTRO PELO CONFERENTE + DEDUPLICAÇÃO
# ------------------------------------------------------------------
def test_conferente_can_request_new_product_registration_with_dedup(isolated_gateway):
    client = isolated_gateway
    _login(client, "CONF-01", "1111")

    payload = {
        "raw_description": "MILHO CONSERVA 6X1.5KG LATA STELLA DORO",
        "suggested_ean": "7898902299999",
        "supplier": "MINAS MAIS",
        "invoice_number": "778899",
        "nf_qty": 2,
        "pack_factor": 6,
        "batch_code": "LOTE-M1",
        "expiration_date": "2027-08-01",
    }

    r1 = client.post("/api/receiving/requests/product", json=payload)
    assert r1.status_code == 201
    req_id = r1.get_json()["request_id"]

    # Reenvio idêntico não deve duplicar na fila
    r2 = client.post("/api/receiving/requests/product", json=payload)
    assert r2.status_code == 200
    assert r2.get_json()["deduplicated"] is True
    assert r2.get_json()["request_id"] == req_id

    # Conferente NÃO pode ler a fila gerencial do Estoquista
    r_forbidden = client.get("/api/receiving/pending")
    assert r_forbidden.status_code == 403


# ------------------------------------------------------------------
# 5. FLUXO PONTA A PONTA: CONFERENTE -> FILA -> ESTOQUISTA APROVA
# ------------------------------------------------------------------
def test_end_to_end_conferente_handoff_to_estoquista_with_replay_guard(isolated_gateway):
    client = isolated_gateway

    # Passo 1: Estoquista pré-cadastra 1 item existente no catálogo
    _login(client, "EST-01", "2222")
    r_existing = client.post(
        "/api/produto",
        json={"name": "GOIABADA STELLA DORO 1,01KG FLOW PACK", "ean": "7898902299171"},
    )
    assert r_existing.status_code == 201
    sku_goiabada = r_existing.get_json()["product"]["id"]
    client.post("/api/auth/logout")

    # Passo 2: Conferente loga, solicita cadastro do item inédito e envia conferência
    _login(client, "CONF-01", "1111")
    r_req = client.post(
        "/api/receiving/requests/product",
        json={
            "raw_description": "MILHO CONSERVA 6X1.5KG LATA STELLA DORO",
            "suggested_ean": "7898902299555",
            "supplier": "STELLA DORO",
            "invoice_number": "90123",
            "nf_qty": 2,
            "pack_factor": 6,
            "batch_code": "L99",
            "expiration_date": "2027-09-15",
        },
    )
    assert r_req.status_code == 201
    req_id = r_req.get_json()["request_id"]

    r_conf_sub = client.post(
        "/api/conference/finalize",
        json={
            "supplier": "STELLA DORO",
            "invoice_number": "90123",
            "items": [
                {
                    "sku": sku_goiabada,
                    "name": "GOIABADA STELLA DORO 1,01KG FLOW PACK",
                    "quantity": 32,
                    "batch_code": "L10",
                    "expiration_date": "2027-06-01",
                },
                {
                    "sku": "TEMP-MILHO15",
                    "name": "MILHO CONSERVA 6X1.5KG LATA STELLA DORO",
                    "quantity": 12,
                    "batch_code": "L99",
                    "expiration_date": "2027-09-15",
                },
            ],
        },
    )
    # Deve retornar 202 (enfileirado) e NÃO alterar o saldo físico ainda
    assert r_conf_sub.status_code == 202
    sub_data = r_conf_sub.get_json()
    assert sub_data["queued"] is True
    queue_id = sub_data["queue_id"]

    assert gateway_app.container.product_repository.get_by_id(sku_goiabada).quantity == 0

    # Tentativa de escalonamento de privilégio: Conferente tenta aprovar a própria fila
    r_esc = client.post(f"/api/receiving/pending/{queue_id}/approve", json={})
    assert r_esc.status_code == 403
    assert gateway_app.container.product_repository.get_by_id(sku_goiabada).quantity == 0
    client.post("/api/auth/logout")

    # Passo 3: Estoquista loga, revisa pendências, cadastra o Milho 1.5KG e aprova entrada
    _login(client, "EST-01", "2222")
    r_pend = client.get("/api/receiving/pending")
    assert r_pend.status_code == 200
    pend_data = r_pend.get_json()
    assert pend_data["pending_products_count"] == 1
    assert pend_data["pending_conferences_count"] == 1

    # Cadastra o produto novo solicitado
    r_new_milho = client.post(
        "/api/produto",
        json={"name": "MILHO CONSERVA 1,5KG LATA STELLA DORO", "ean": "7898902299555"},
    )
    assert r_new_milho.status_code == 201
    sku_milho = r_new_milho.get_json()["product"]["id"]

    # Resolve solicitação de produto (grava também De-Para e fator 6)
    r_res_prod = client.post(
        f"/api/receiving/pending/{req_id}/resolve-product",
        json={
            "action": "CADASTRADO",
            "sku": sku_milho,
            "ean": "7898902299555",
            "name": "MILHO CONSERVA 1,5KG LATA STELLA DORO",
        },
    )
    assert r_res_prod.status_code == 200

    # Aprova conferência vinculando o índice 1 (TEMP-MILHO15) ao SKU recém-criado
    r_approve = client.post(
        f"/api/receiving/pending/{queue_id}/approve",
        json={"sku_overrides": {"1": sku_milho}},
    )
    assert r_approve.status_code == 200
    assert r_approve.get_json()["approved"] == 2

    # Valida saldos reais no estoque após aprovação do Estoquista
    assert gateway_app.container.product_repository.get_by_id(sku_goiabada).quantity == 32
    assert gateway_app.container.product_repository.get_by_id(sku_milho).quantity == 12

    # Valida trava contra dupla aprovação (Replay Guard)
    r_replay = client.post(
        f"/api/receiving/pending/{queue_id}/approve",
        json={"sku_overrides": {"1": sku_milho}},
    )
    assert r_replay.status_code == 409
    assert gateway_app.container.product_repository.get_by_id(sku_goiabada).quantity == 32
    assert gateway_app.container.product_repository.get_by_id(sku_milho).quantity == 12


# ------------------------------------------------------------------
# 6. CONTRATO DE INTERFACE FRONTEND (JS)
# ------------------------------------------------------------------
def test_frontend_role_separation_contracts():
    app_js = Path("web/js/app.js").read_text()
    conf_js = Path("web/js/features/conference.js").read_text()

    assert "canManageCatalog()" in app_js
    assert "ESTOQUISTA" in app_js
    assert "ADMIN_SISTEMA" in app_js
    assert "refreshEstoquistaPendingQueue" in app_js

    assert "isConferenceOnlyRole()" in conf_js
    assert "SOLICITAR CADASTRO AO ESTOQUISTA" in conf_js
    assert "ENVIAR PARA ARMAZENAGEM" in conf_js
    assert "nf-multiphoto-modal" in conf_js
    assert "ai-upload-gallery" in conf_js
    assert "uploadNfPhotoBatch" in conf_js


def test_adobe_scan_embedded_jpeg_with_exif_marker_extraction():
    """
    Garante que um PDF com XRef quebrado e JPEG embutido contendo miniatura EXIF (\xff\xd9)
    dentro de segmento APP1 antes do endstream seja extraído integralmente sem truncamento.
    """
    import io
    import struct
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (600, 800), color=(240, 240, 240)).save(buf, format="JPEG", quality=90)
    real_jpeg = buf.getvalue()

    # Constrói segmento APP1 EXIF válido contendo uma miniatura com marcador \xff\xd9
    exif_payload = b"Exif\x00\x00" + b"\xff\xd8\xff\xdb" + (b"\x00" * 64) + b"\xff\xd9"
    app1_segment = b"\xff\xe1" + struct.pack(">H", len(exif_payload) + 2) + exif_payload
    jpeg_with_exif_thumb = real_jpeg[:2] + app1_segment + real_jpeg[2:]

    broken_pdf = (
        b"%PDF-1.4\n1 0 obj\n<< /Type /XObject /Subtype /Image >>\nstream\n"
        + jpeg_with_exif_thumb
        + b"\nendstream\nendobj\nxref\n0 1\n0000000000 65535 n \n%%EOF"
    )

    extracted = gateway_app._extract_embedded_jpegs_from_pdf(broken_pdf)
    assert len(extracted) == 1
    assert extracted[0].size == (600, 800)


def test_multi_page_invoice_photo_ocr_consolidation(isolated_gateway, monkeypatch):
    """
    Garante que o endpoint POST /api/invoices/ocr aceite múltiplas fotos (files[])
    de uma nota fiscal de várias páginas e consolide fornecedor, número da NF e itens.
    """
    import io

    client = isolated_gateway
    _login(client, "CONF-01", "1111")

    def fake_single_ocr(file_bytes, filename="", mimetype=""):
        text = file_bytes.decode("utf-8", errors="ignore")
        if "PAG1" in text:
            yield {
                "progress": 100,
                "done": True,
                "supplier": "ATACADAO DISTRIBUIDOR LTDA",
                "invoice_number": "987654",
                "items": [{"description": "ARROZ TIPO 1 5KG", "quantity": 10, "pack_factor": 1}],
            }
        else:
            yield {
                "progress": 100,
                "done": True,
                "supplier": "",
                "invoice_number": "",
                "items": [{"description": "FEIJAO CARIOCA 1KG", "quantity": 20, "pack_factor": 1}],
            }

    monkeypatch.setattr(gateway_app, "_iter_invoice_ocr", fake_single_ocr)

    data = {
        "files": [
            (io.BytesIO(b"PAG1_IMAGE_BYTES"), "pag1.jpg", "image/jpeg"),
            (io.BytesIO(b"PAG2_IMAGE_BYTES"), "pag2.jpg", "image/jpeg"),
        ]
    }
    res = client.post("/api/invoices/ocr", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    body = res.get_json()
    assert body["supplier"] == "ATACADAO DISTRIBUIDOR LTDA"
    assert body["invoice_number"] == "987654"
    assert body["pages_processed"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["description"] == "ARROZ TIPO 1 5KG"
    assert body["items"][1]["description"] == "FEIJAO CARIOCA 1KG"


def test_admin_can_create_list_and_delete_profiles_with_rbac_guards(isolated_gateway):
    """
    Garante que:
    1. Conferente e Estoquista recebem 403 ao tentar listar, criar ou excluir perfis.
    2. ADMIN_SISTEMA cria um novo CONFERENTE via API, o Conferente faz login imediatamente,
       e o ADMIN_SISTEMA consegue listar e excluir o perfil depois.
    3. ADMIN_SISTEMA é impedido de excluir o próprio perfil ativo.
    """
    client = isolated_gateway

    # Conferente bloqueado (403)
    _login(client, "CONF-01", "1111")
    assert client.get("/api/operators").status_code == 403
    assert client.post("/api/operators", json={"id": "HACK", "name": "HACK", "pin": "1234", "role": "ADMIN_SISTEMA"}).status_code == 403
    assert client.delete("/api/operators/EST-01").status_code == 403
    client.post("/api/auth/logout")

    # Estoquista bloqueado (403)
    _login(client, "EST-01", "2222")
    assert client.get("/api/operators").status_code == 403
    assert client.post("/api/operators", json={"id": "HACK2", "name": "HACK2", "pin": "1234", "role": "CONFERENTE"}).status_code == 403
    client.post("/api/auth/logout")

    # Admin Sistema cria novo Conferente
    _login(client, "ADM-01", "9999")
    r_create = client.post(
        "/api/operators",
        json={"id": "CONF-02", "name": "JOAO DOCA", "pin": "4321", "role": "CONFERENTE"},
    )
    assert r_create.status_code == 201

    r_list = client.get("/api/operators")
    assert r_list.status_code == 200
    ids = [op["id"] for op in r_list.get_json()["operators"]]
    assert "CONF-02" in ids

    # Admin não pode excluir o próprio perfil ativo
    r_self = client.delete("/api/operators/ADM-01")
    assert r_self.status_code == 400
    assert "próprio perfil" in r_self.get_json()["error"]

    # Novo Conferente consegue logar imediatamente
    client.post("/api/auth/logout")
    op_new = _login(client, "CONF-02", "4321")
    assert op_new["role"] == "CONFERENTE"
    assert op_new["name"] == "JOAO DOCA"
    client.post("/api/auth/logout")

    # Admin exclui o perfil CONF-02
    _login(client, "ADM-01", "9999")
    r_del = client.delete("/api/operators/CONF-02")
    assert r_del.status_code == 200
    assert gateway_app.container.operator_repository.get_by_id("CONF-02") is None


def test_frontend_admin_team_management_contract():
    app_js = Path("web/js/app.js").read_text()
    assert "openTeamProfilesModal" in app_js
    assert "syncAdminTeamButton" in app_js
    assert "/api/operators" in app_js
