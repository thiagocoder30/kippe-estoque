from src.infrastructure.db_adapter import connect_db, is_postgres_enabled
from src.domain.access_control import AccessControl
import re
import unicodedata
import sqlite3
from PIL import ImageOps
import threading
from flask import Response, stream_with_context
import time
from pathlib import Path
from flask import redirect
import shutil
import uuid
import tempfile
import subprocess
import base64
import urllib.error
import urllib.request
import io
import json
import os
from PIL import Image, ImageDraw
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False
from flask import Flask, jsonify, request, session, send_from_directory, send_file
from src.infrastructure.container import Container
from src.domain.services.expiration_analyzer import ExpirationAnalyzer
from src.application.procurement.invoice_preparation import (
    ExtractedInvoiceData,
    ExtractedInvoiceLineData,
)
from src.application.procurement.operator_receiving_integration import (
    OperatorReceivingIntegrationService,
)

from src.application.procurement.danfe_http_acquisition import (
    DanfeHttpAcquisitionError,
    DanfeHttpAcquisitionService,
)

container = Container()
load_dotenv()
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024
app.secret_key = container.config.SECRET_KEY


def _has_valid_session():
    if (
        container.config.ENV == "testing"
        and "X-Test-Operator-Override" in request.headers
    ):
        return True

    return 'operator_id' in session


@app.route('/')
def index():
    return send_from_directory('web', 'index.html')


@app.route('/web/<path:filename>', methods=['GET'])
def web_assets(filename):
    return send_from_directory('web', filename)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'system': 'KIPPE WMS',
        'gateway': 'flask'
    }), 200


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}

    res = container.auth_use_case.authenticate(
        data.get('id'),
        data.get('pin')
    )

    if res.is_success:
        session['operator_id'] = res.value.id
        session['operator_name'] = res.value.name
        session['operator_role'] = res.value.role
        _record_audit_event(
            "AUTH_LOGIN",
            "ACESSO",
            f"Login realizado por {res.value.name} ({res.value.role})",
            target_ref=res.value.id,
            actor_override=(res.value.id, res.value.name, res.value.role),
        )

        return jsonify({
            'message': 'OK',
            'operator': {
                'id': res.value.id,
                'name': res.value.name,
                'role': res.value.role
            }
        }), 200

    return jsonify({
        'error': res.error
    }), 401


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    ctx_out = _get_active_operator_context()
    if ctx_out[0]:
        _record_audit_event(
            "AUTH_LOGOUT",
            "ACESSO",
            f"Sessão encerrada por {ctx_out[1]}",
            target_ref=ctx_out[0],
            actor_override=ctx_out,
        )
    session.clear()

    return jsonify({
        'message': 'Sessão encerrada'
    }), 200



@app.route('/api/operators', methods=['GET'])
def list_operators_api():
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    _, _, op_role = _get_active_operator_context()
    if not AccessControl.is_system_admin(op_role):
        return jsonify({'error': 'Autorização negada: apenas Administrador do Sistema gerencia perfis.'}), 403

    operators = container.auth_use_case.list_operators()
    return jsonify({
        'operators': [
            {'id': op.id, 'name': op.name, 'role': op.role}
            for op in operators
        ]
    }), 200


@app.route('/api/operators', methods=['POST'])
def create_operator_api():
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    actor_id, _, op_role = _get_active_operator_context()
    if not AccessControl.is_system_admin(op_role):
        return jsonify({'error': 'Autorização negada: apenas Administrador do Sistema pode criar perfis.'}), 403

    data = request.json or {}
    new_id = str(data.get('id') or '').strip().upper()
    new_name = str(data.get('name') or '').strip().upper()
    new_pin = str(data.get('pin') or '').strip()
    new_role = str(data.get('role') or 'CONFERENTE').strip().upper()

    if not new_id or not new_name:
        return jsonify({'error': 'Informe a matrícula/ID e o nome do colaborador.'}), 400

    res = container.auth_use_case.register(
        id=new_id,
        name=new_name,
        pin=new_pin,
        role=new_role,
    )
    if not res.is_success:
        return jsonify({'error': res.error}), 400

    _record_audit_event(
        "OPERATOR_CREATED",
        "GOVERNANCA",
        f"Perfil {new_role} criado para {new_name} (ID: {new_id})",
        target_ref=new_id,
    )
    return jsonify({
        'ok': True,
        'operator': {'id': new_id, 'name': new_name, 'role': new_role},
        'message': f'Perfil {new_role} criado para {new_name}.',
    }), 201


@app.route('/api/operators/<op_id>', methods=['DELETE'])
def delete_operator_api(op_id: str):
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    actor_id, _, op_role = _get_active_operator_context()
    if not AccessControl.is_system_admin(op_role):
        return jsonify({'error': 'Autorização negada: apenas Administrador do Sistema pode excluir perfis.'}), 403

    res = container.auth_use_case.delete_operator(target_id=op_id, actor_id=actor_id)
    if not res.is_success:
        return jsonify({'error': res.error}), 400

    _record_audit_event(
        "OPERATOR_DELETED",
        "GOVERNANCA",
        f"Perfil [{op_id}] excluído da equipe",
        target_ref=str(op_id),
    )
    return jsonify({'ok': True, 'message': 'Perfil excluído com sucesso.'}), 200



def _record_audit_event(
    event_type: str,
    category: str,
    summary: str,
    target_ref: str = "",
    details: dict = None,
    actor_override: tuple = None,
):
    try:
        if actor_override:
            actor_id, actor_name, actor_role = actor_override
        else:
            actor_id, actor_name, actor_role = _get_active_operator_context()
        actor_id = str(actor_id or "SYSTEM").strip()
        actor_name = str(actor_name or actor_id or "SYSTEM").strip()
        actor_role = str(actor_role or "SYSTEM").strip().upper()
        now_iso = __import__('datetime').datetime.now().isoformat(timespec='seconds')
        conn = _get_kippe_db()
        try:
            conn.execute(
                '''
                INSERT INTO institutional_audit_log (
                    event_type, category, actor_id, actor_name, actor_role,
                    target_ref, summary, details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    str(event_type).strip().upper(),
                    str(category).strip().upper(),
                    actor_id,
                    actor_name,
                    actor_role,
                    str(target_ref or "").strip(),
                    str(summary).strip(),
                    json.dumps(details or {}, ensure_ascii=False),
                    now_iso,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass


@app.route('/api/operators/<op_id>/pin', methods=['PATCH'])
def reset_operator_pin_api(op_id: str):
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    actor_id, _, op_role = _get_active_operator_context()
    if not AccessControl.is_system_admin(op_role):
        return jsonify({'error': 'Autorização negada: apenas Administrador do Sistema pode redefinir PIN.'}), 403

    data = request.json or {}
    new_pin = str(data.get('pin') or '').strip()
    target = container.operator_repository.get_by_id(str(op_id or '').strip())
    res = container.auth_use_case.reset_pin(target_id=op_id, new_pin=new_pin, actor_id=actor_id)
    if not res.is_success:
        return jsonify({'error': res.error}), 400

    target_label = f"{target.name} ({target.id})" if target else op_id
    _record_audit_event(
        "OPERATOR_PIN_RESET",
        "GOVERNANCA",
        f"PIN redefinido para {target_label}",
        target_ref=str(op_id),
    )
    return jsonify({'ok': True, 'message': 'PIN redefinido com sucesso.'}), 200


@app.route('/api/auth/change-pin', methods=['POST'])
def change_own_pin_api():
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    actor_id, actor_name, actor_role = _get_active_operator_context()
    data = request.json or {}
    current_pin = str(data.get('current_pin') or '').strip()
    new_pin = str(data.get('new_pin') or '').strip()

    res = container.auth_use_case.change_own_pin(
        operator_id=actor_id,
        current_pin=current_pin,
        new_pin=new_pin,
    )
    if not res.is_success:
        return jsonify({'error': res.error}), 400

    _record_audit_event(
        "OPERATOR_PIN_CHANGED",
        "ACESSO",
        f"{actor_name} alterou o próprio PIN de acesso",
        target_ref=actor_id,
        actor_override=(actor_id, actor_name, actor_role),
    )
    return jsonify({'ok': True, 'message': 'Seu PIN foi atualizado com sucesso.'}), 200


@app.route('/api/audit/logs', methods=['GET'])
def list_audit_logs_api():
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    _, _, op_role = _get_active_operator_context()
    if not AccessControl.is_system_admin(op_role):
        return jsonify({'error': 'Autorização negada: apenas Administrador do Sistema acessa a auditoria.'}), 403

    category = str(request.args.get('category') or 'ALL').strip().upper()
    q = str(request.args.get('q') or '').strip().upper()
    try:
        limit = min(200, max(10, int(request.args.get('limit') or 100)))
    except Exception:
        limit = 100

    conn = _get_kippe_db()
    try:
        rows = conn.execute(
            "SELECT * FROM institutional_audit_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    logs = []
    for r in rows:
        item = {
            'id': int(r['id']),
            'event_type': r['event_type'],
            'category': r['category'],
            'actor_id': r['actor_id'],
            'actor_name': r['actor_name'],
            'actor_role': r['actor_role'],
            'target_ref': r['target_ref'] or '',
            'summary': r['summary'],
            'created_at': r['created_at'],
        }
        if category != 'ALL' and item['category'] != category:
            continue
        if q:
            haystack = f"{item['actor_id']} {item['actor_name']} {item['actor_role']} {item['target_ref']} {item['summary']}".upper()
            if q not in haystack:
                continue
        logs.append(item)

    return jsonify({'total': len(logs), 'logs': logs}), 200



@app.route('/api/admin/backup', methods=['POST'])
def create_sqlite_backup_api():
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    _, _, op_role = _get_active_operator_context()
    if not AccessControl.is_system_admin(op_role):
        return jsonify({'error': 'Autorização negada: apenas Administrador do Sistema pode gerar backups.'}), 403

    import hashlib
    import shutil
    from datetime import datetime

    if is_postgres_enabled():
        import hashlib
        from datetime import datetime

        tables_to_dump = [
            "categories", "products", "batches", "operators", "transactions",
            "operational_audit_events", "sku_sequences", "sku_aliases",
            "sku_pack_defaults", "receiving_pending_queue",
            "product_registration_requests", "institutional_audit_log",
            "receiving_divergences", "conference_audit_log",
        ]
        conn_pg = connect_db()
        snapshot = {"engine": "postgresql", "exported_at": datetime.now().isoformat(), "tables": {}}
        try:
            for tbl in tables_to_dump:
                try:
                    rows = conn_pg.execute(f"SELECT * FROM {tbl}").fetchall()
                    snapshot["tables"][tbl] = [dict(r) for r in rows]
                except Exception:
                    snapshot["tables"][tbl] = []
        finally:
            conn_pg.close()

        raw_json = json.dumps(snapshot, ensure_ascii=False, default=str, indent=2).encode("utf-8")
        sha256_hex = hashlib.sha256(raw_json).hexdigest()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"kippe_supabase_snapshot_{stamp}.json"
        return Response(
            raw_json,
            mimetype="application/json; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Backup-SHA256": sha256_hex,
            },
        )

    src_db_path = Path(container.config.DB_PATH).resolve()
    if not src_db_path.exists():
        return jsonify({'error': f'Banco de dados não encontrado em {src_db_path}.'}), 404

    backups_dir = Path("backups").resolve()
    backups_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"kippe_wms_backup_{stamp}.db"
    dst_db_path = backups_dir / filename

    try:
        src_conn = sqlite3.connect(str(src_db_path))
        dst_conn = sqlite3.connect(str(dst_db_path))
        try:
            src_conn.backup(dst_conn)
            dst_conn.commit()
            integrity_row = dst_conn.execute("PRAGMA integrity_check;").fetchone()
            integrity_status = str(integrity_row[0]).strip().lower() if integrity_row else "error"
        finally:
            dst_conn.close()
            src_conn.close()

        if integrity_status != "ok":
            dst_db_path.unlink(missing_ok=True)
            return jsonify({'error': f'Falha na verificação de integridade do backup: {integrity_status}'}), 500

        raw_bytes = dst_db_path.read_bytes()
        sha256_hex = hashlib.sha256(raw_bytes).hexdigest()
        size_bytes = len(raw_bytes)

        # Mantém apenas os 15 backups locais mais recentes
        existing_backups = sorted(backups_dir.glob("kippe_wms_backup_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old_bk in existing_backups[15:]:
            old_bk.unlink(missing_ok=True)

        # Em produção no Termux, salva também em /sdcard/Download se disponível
        download_folder_saved = False
        external_path = ""
        if container.config.ENV != "testing":
            android_dl = Path("/sdcard/Download")
            if android_dl.exists() and android_dl.is_dir():
                try:
                    ext_target = android_dl / filename
                    shutil.copy2(dst_db_path, ext_target)
                    download_folder_saved = True
                    external_path = str(ext_target)
                except Exception:
                    download_folder_saved = False

        _record_audit_event(
            "SYSTEM_BACKUP_CREATED",
            "GOVERNANCA",
            f"Backup íntegro SQLite gerado: {filename} ({size_bytes} bytes · SHA256 {sha256_hex[:12]})",
            target_ref=filename,
        )

        return jsonify({
            'ok': True,
            'filename': filename,
            'size_bytes': size_bytes,
            'sha256': sha256_hex,
            'integrity': 'ok',
            'download_folder_saved': download_folder_saved,
            'external_path': external_path,
            'download_url': f'/api/admin/backup/download/{filename}',
        }), 201
    except Exception as exc:
        dst_db_path.unlink(missing_ok=True)
        return jsonify({'error': f'Erro ao gerar backup: {exc}'}), 500


@app.route('/api/admin/backup/download/<filename>', methods=['GET'])
def download_sqlite_backup_api(filename: str):
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    _, _, op_role = _get_active_operator_context()
    if not AccessControl.is_system_admin(op_role):
        return jsonify({'error': 'Autorização negada.'}), 403

    safe_name = Path(filename).name
    if not safe_name.startswith("kippe_wms_backup_") or not safe_name.endswith(".db"):
        return jsonify({'error': 'Nome de arquivo de backup inválido.'}), 400

    target = (Path("backups").resolve() / safe_name)
    if not target.exists() or not target.is_file():
        return jsonify({'error': 'Arquivo de backup não encontrado.'}), 404

    return send_file(
        str(target),
        mimetype='application/x-sqlite3',
        as_attachment=True,
        download_name=safe_name,
    )


@app.route('/api/reports/export/<report_type>.csv', methods=['GET'])
def export_management_csv_api(report_type: str):
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    _, _, op_role = _get_active_operator_context()
    role_norm = str(op_role or '').strip().upper()
    if not (AccessControl.is_system_admin(role_norm) or role_norm == 'GERENTE'):
        return jsonify({'error': 'Autorização negada: apenas Administrador ou Gerente pode exportar relatórios.'}), 403

    import csv
    import io
    from datetime import date, datetime

    rtype = str(report_type or '').strip().lower()
    if rtype not in {'inventario', 'fefo', 'recebimentos', 'divergencias'}:
        return jsonify({'error': 'Tipo de relatório inválido. Use: inventario, fefo ou recebimentos.'}), 400

    conn = connect_db(str(container.config.DB_PATH))
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=';', lineterminator='\n')

    try:
        if rtype == 'inventario':
            writer.writerow([
                'SKU', 'EAN', 'Produto', 'Categoria', 'Unidade',
                'Saldo_Total', 'Reservado', 'Disponivel',
                'Qtd_Lotes', 'Proximo_Vencimento', 'Status'
            ])
            rows = conn.execute(
                '''
                SELECT
                    p.id AS sku,
                    p.ean AS ean,
                    p.name AS product_name,
                    COALESCE(c.name, 'SEM CATEGORIA') AS category_name,
                    p.unit_of_measure AS uom,
                    p.quantity AS qty_total,
                    p.reserved_quantity AS qty_reserved,
                    (p.quantity - p.reserved_quantity) AS qty_available,
                    p.status AS status,
                    COUNT(CASE WHEN b.quantity > 0 THEN 1 END) AS active_batches,
                    MIN(CASE WHEN b.quantity > 0 THEN NULLIF(b.expiration_date, '') END) AS next_exp
                FROM products p
                LEFT JOIN categories c ON c.id = p.category_id
                LEFT JOIN batches b ON b.product_id = p.id
                GROUP BY p.id
                ORDER BY p.name ASC
                '''
            ).fetchall()
            for r in rows:
                writer.writerow([
                    r['sku'], r['ean'], r['product_name'], r['category_name'], r['uom'],
                    r['qty_total'], r['qty_reserved'], r['qty_available'],
                    r['active_batches'], r['next_exp'] or '', r['status'],
                ])

        elif rtype == 'fefo':
            writer.writerow([
                'SKU', 'Produto', 'EAN', 'Lote', 'Validade',
                'Dias_Para_Vencer', 'Faixa_Risco', 'Quantidade',
                'Endereco', 'Fornecedor', 'Custo_Unitario', 'Valor_Total'
            ])
            rows = conn.execute(
                '''
                SELECT
                    b.product_id AS sku,
                    COALESCE(p.name, b.product_id) AS product_name,
                    COALESCE(p.ean, '') AS ean,
                    b.batch_code,
                    b.expiration_date,
                    b.quantity,
                    b.location_id,
                    b.supplier,
                    b.cost_per_unit
                FROM batches b
                LEFT JOIN products p ON p.id = b.product_id
                WHERE b.quantity > 0
                ORDER BY
                    CASE WHEN COALESCE(b.expiration_date, '') = '' THEN 1 ELSE 0 END ASC,
                    b.expiration_date ASC,
                    product_name ASC
                '''
            ).fetchall()
            today = date.today()
            for r in rows:
                exp_str = str(r['expiration_date'] or '').strip()
                days_str = ''
                risk_label = 'SEM_VALIDADE'
                if exp_str:
                    try:
                        exp_dt = date.fromisoformat(exp_str[:10])
                        diff = (exp_dt - today).days
                        days_str = str(diff)
                        if diff < 0:
                            risk_label = 'VENCIDO'
                        elif diff <= 15:
                            risk_label = 'CRITICO_15D'
                        elif diff <= 30:
                            risk_label = 'ATENCAO_30D'
                        else:
                            risk_label = 'NORMAL'
                    except Exception:
                        risk_label = 'DATA_INVALIDA'

                qty = int(r['quantity'] or 0)
                unit_cost = float(r['cost_per_unit'] or 0.0)
                total_val = round(qty * unit_cost, 2)
                writer.writerow([
                    r['sku'], r['product_name'], r['ean'], r['batch_code'], exp_str,
                    days_str, risk_label, qty,
                    r['location_id'] or '', r['supplier'] or 'PADRAO',
                    f"{unit_cost:.2f}", f"{total_val:.2f}",
                ])

        elif rtype == 'recebimentos':
            writer.writerow([
                'ID_Evento', 'Data_Hora', 'Tipo_Evento', 'SKU', 'Produto',
                'Lote', 'Qtd_Prevista', 'Qtd_Conferida', 'Divergencia',
                'Fornecedor', 'Documento_NF', 'Operador'
            ])
            rows = conn.execute(
                '''
                SELECT
                    e.id,
                    e.occurred_at,
                    e.event_type,
                    e.product_id,
                    COALESCE(p.name, e.product_id) AS product_name,
                    e.batch_code,
                    e.quantity_planned,
                    e.quantity_actual,
                    e.quantity_divergence,
                    e.supplier,
                    e.document_id,
                    e.operator_id
                FROM operational_audit_events e
                LEFT JOIN products p ON p.id = e.product_id
                ORDER BY e.id DESC
                '''
            ).fetchall()
            for r in rows:
                writer.writerow([
                    r['id'],
                    r['occurred_at'] or '',
                    r['event_type'] or '',
                    r['product_id'] or '',
                    r['product_name'] or '',
                    r['batch_code'] or '',
                    r['quantity_planned'] if r['quantity_planned'] is not None else '',
                    r['quantity_actual'] if r['quantity_actual'] is not None else '',
                    r['quantity_divergence'] if r['quantity_divergence'] is not None else '',
                    r['supplier'] or '',
                    r['document_id'] or '',
                    r['operator_id'] or '',
                ])
        elif rtype == 'divergencias':
            writer.writerow([
                'ID', 'Data_Hora', 'Fornecedor', 'Numero_NF', 'SKU', 'Produto',
                'Qtd_Faturada_NF', 'Qtd_Conferida', 'Divergencia',
                'Motivo_Formal', 'Observacoes', 'Operador_ID', 'Operador_Nome'
            ])
            conn_div = _get_kippe_db()
            try:
                rows_div = conn_div.execute(
                    "SELECT * FROM receiving_divergences ORDER BY id DESC"
                ).fetchall()
            finally:
                conn_div.close()
            for r in rows_div:
                writer.writerow([
                    r['id'], r['created_at'], r['supplier'], r['invoice_number'],
                    r['sku'], r['product_name'], r['expected_qty'], r['counted_qty'],
                    r['divergence_qty'], r['reason'], r['notes'] or '',
                    r['operator_id'], r['operator_name'],
                ])

    finally:
        conn.close()

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_name = f"kippe_{rtype}_{stamp}.csv"

    _record_audit_event(
        "REPORT_EXPORTED",
        "GOVERNANCA",
        f"Relatório gerencial CSV exportado: {out_name}",
        target_ref=out_name,
    )

    csv_payload = ("\ufeff" + buf.getvalue()).encode("utf-8")
    return Response(
        csv_payload,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{out_name}"',
            "Cache-Control": "no-cache",
        },
    )


@app.route('/api/auth/me', methods=['GET'])
def me():
    if _has_valid_session():
        op_id = (
            request.headers.get(
                "X-Test-Operator-Override"
            )
            if (
                container.config.ENV == "testing"
                and "X-Test-Operator-Override"
                in request.headers
            )
            else session.get('operator_id')
        )

        return jsonify({
            'authenticated': True,
            'operator': {
                'id': op_id,
                'name': session.get(
                    'operator_name',
                    'Test Agent'
                ),
                'role': session.get(
                    'operator_role',
                    'OPERADOR'
                )
            }
        })

    return jsonify({
        'authenticated': False
    }), 200


@app.route('/api/categorias', methods=['GET'])
def get_categorias():
    return jsonify([
        {
            'id': category.id,
            'name': category.name,
            'parent_id': category.parent_id
        }
        for category
        in container.category_use_case.list_all()
    ])


@app.route('/api/categoria', methods=['POST'])
def create_categoria():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    res = container.category_use_case.create_category(
        data.get('id'),
        data.get('name'),
        data.get('parent_id')
    )

    if res.is_success:
        return jsonify({
            'message': 'OK'
        }), 201

    if "Autorização negada" in res.error:
        return jsonify({
            "error": res.error
        }), 403

    return jsonify({
        'error': res.error
    }), 400


@app.route('/api/produtos', methods=['GET'])
def get_produtos():
    return jsonify([
        {
            'id': product.id,
            'name': product.name,
            'quantity': product.quantity
        }
        for product
        in container.use_case.list_all()
    ])


@app.route('/api/produto/<sku>', methods=['GET'])
@app.route('/api/sku/<sku>', methods=['GET'])
def get_produto(sku):
    product = container.product_repository.get_by_id(
        sku
    )

    if not product:
        return jsonify({
            'error': 'Not found'
        }), 404

    return jsonify({
        'id': product.id,
        'name': product.name,
        'quantity': product.quantity
    })


@app.route('/api/reposicao/<sku>', methods=['GET'])
def get_picking_info(sku):
    res = container.use_case.get_picking_info(
        sku
    )

    if res.is_success:
        return jsonify(
            res.value
        )

    return jsonify({
        'error': res.error
    }), 404


# ========================================================
# PROTECTED ROUTES (HTTP Auth Normalization 401)
# ========================================================

@app.route('/api/produto', methods=['POST'])
def create_produto():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    explicit_product_id = data.get(
        'id'
    )

    # Compatibilidade temporária:
    # integrações e testes internos antigos ainda podem
    # cadastrar um produto usando um SKU explícito.
    if explicit_product_id:
        res = container.use_case.create_product(
            product_id=explicit_product_id,
            name=data.get('name'),
            unit_of_measure=data.get(
                'unit_of_measure',
                'un'
            ),
            status=data.get(
                'status',
                'ATIVO'
            ),
            category_id=data.get(
                'category_id'
            ),
            ean=data.get(
                'ean',
                ''
            ),
        )

        if res.is_success:
            return jsonify({
                'message': 'OK'
            }), 201

    else:
        # Contrato operacional canônico:
        # o cliente não controla o SKU.
        res = container.use_case.register_product(
            name=data.get('name'),
            ean=data.get(
                'ean',
                ''
            ),
            unit_of_measure=data.get(
                'unit_of_measure',
                'un'
            ),
            status=data.get(
                'status',
                'ATIVO'
            ),
            category_id=data.get(
                'category_id'
            ),
        )

        if res.is_success:
            p_val = res.value or {}
            _record_audit_event(
                "PRODUCT_CREATED",
                "CATALOGO",
                f"Produto cadastrado: {p_val.get('name', data.get('name', ''))} (SKU: {p_val.get('id', '')})",
                target_ref=str(p_val.get('id', '')),
            )
            return jsonify({
                'message': 'Produto cadastrado.',
                'product': res.value
            }), 201

    if (
        'Autorização negada'
        in res.error
    ):
        return jsonify({
            'error': res.error
        }), 403

    if (
        'EAN' in res.error
        and 'já' in res.error.lower()
    ):
        return jsonify({
            'error': res.error
        }), 409

    return jsonify({
        'error': res.error
    }), 400


@app.route('/api/adjustment', methods=['POST'])
def adjustment_stock():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    product_id = (
        data.get('sku')
        or data.get('id')
    )

    amount = (
        data.get('quantity')
        or data.get('amount')
    )

    reason = (
        data.get('divergence_type')
        or data.get('reason')
        or "CONTAGEM"
    )

    res = container.use_case.execute_adjustment(
        product_id,
        amount,
        reason,
        data.get('batch_code'),
        data.get(
            'warehouse_id',
            'WH-PADRAO'
        )
    )

    if res.is_success:
        return jsonify({
            'message': 'Ajuste registrado.'
        }), 200

    return jsonify({
        'error': res.error
    }), 400


@app.route('/api/product/suggestions', methods=['GET'])
def suggest_products():
    query = request.args.get(
        'q',
        ''
    ).strip()

    if not query:
        return jsonify([]), 200

    products = (
        container
        .product_suggestion_use_case
        .execute(
            query=query
        )
    )

    return jsonify([
        {
            'id': product.id,
            'name': product.name,
            'ean': product.ean,
        }
        for product in products
    ]), 200


@app.route('/api/product/query', methods=['GET'])
def query_product():
    identifier = request.args.get(
        'identifier',
        ''
    ).strip()

    if not identifier:
        return jsonify({
            'error': 'Identificador obrigatório.'
        }), 400

    res = (
        container
        .product_query_use_case
        .execute(
            identifier=identifier
        )
    )

    if res.is_success:
        return jsonify(
            res.value
        ), 200

    if (
        res.error
        == 'PRODUTO_NAO_CADASTRADO'
    ):
        return jsonify({
            'error': res.error
        }), 404

    return jsonify({
        'error': res.error
    }), 400


@app.route(
    '/api/products/<product_id>/history',
    methods=['GET']
)
def product_operational_history(product_id):
    if not _has_valid_session():
        return jsonify({
            'success': False,
            'error': 'Operador não autenticado.'
        }), 401

    normalized_product_id = str(
        product_id
    ).strip()

    product = (
        container
        .repository
        .get_by_id(
            normalized_product_id
        )
    )

    if product is None:
        return jsonify({
            'success': False,
            'error': 'PRODUTO_NAO_CADASTRADO',
            'product_id': normalized_product_id,
        }), 404

    events = (
        container
        .repository
        .get_operational_audit_events_by_product(
            normalized_product_id
        )
    )

    events = sorted(
        list(events or []),
        key=lambda event: (
            int(event.get('id') or 0)
        ),
    )

    receiving_events = [
        event
        for event in events
        if event.get('event_type')
        == 'RECEBIMENTO'
    ]

    latest_receiving = (
        receiving_events[-1]
        if receiving_events
        else None
    )

    return jsonify({
        'success': True,
        'product_id': normalized_product_id,
        'latest_receiving': latest_receiving,
        'events': events,
    }), 200


@app.route(
    '/api/relatorios/vencimentos',
    methods=['GET']
)
def expiration_report():
    """Relatorio de vencimentos com separacao estoque/loja e faixas de urgencia."""

    report = []
    products = container.product_repository.get_all()

    def classify(days_remaining: int) -> str:
        if days_remaining < 0:
            return "expired"
        if days_remaining <= 7:
            return "critical"
        if days_remaining <= 30:
            return "warning"
        if days_remaining <= 90:
            return "attention"
        return "safe"

    for product in products:
        for batch in product.batches.values():
            analysis = ExpirationAnalyzer.analyze(batch.expiration_date)
            if not analysis.is_success:
                continue
                
            # Ignora lotes vazios (já abastecidos ou esgotados)
            if batch.quantity <= 0:
                continue
                
            expiration = analysis.value
            days = expiration["days_remaining"]

            warehouse_id = getattr(batch, "warehouse_id", "WH-PADRAO")
            is_store = bool(warehouse_id) and (
                "LOJA" in warehouse_id.upper() or "STORE" in warehouse_id.upper()
            )

            report.append({
                "sku": product.id,
                "ean": product.ean,
                "name": product.name,
                "batch": batch.code,
                "expiration": batch.expiration_date,
                "days_remaining": days,
                "status": expiration["status"],
                "urgency": classify(days),
                "quantity": batch.quantity,
                "warehouse_id": warehouse_id,
                "location": "store" if is_store else "depot",
                "location_id": batch.location_id,
            })

    report.sort(key=lambda item: (item["days_remaining"], item["name"], item["batch"]))

    summary = {"expired": 0, "critical": 0, "warning": 0, "attention": 0, "safe": 0}
    for item in report:
        summary[item["urgency"]] += 1

    return jsonify({
        "items": report,
        "summary": summary,
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }), 200


@app.route(
    '/api/abastecimento/plano',
    methods=['POST']
)
def replenishment_plan():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    res = (
        container
        .use_case
        .plan_replenishment(
            data.get('items')
        )
    )

    if res.is_success:
        return jsonify(
            res.value
        ), 200

    return jsonify({
        'error': res.error
    }), 400


@app.route(
    '/api/abastecimento/coleta/plano',
    methods=['POST']
)
def replenishment_pick_plan():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    res = (
        container
        .use_case
        .plan_replenishment_pick(
            data.get('items')
        )
    )

    if res.is_success:
        return jsonify(
            res.value
        ), 200

    return jsonify({
        'error': res.error
    }), 400


@app.route(
    '/api/abastecimento/coleta/confirmar',
    methods=['POST']
)
def replenishment_pick_confirm():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    res = (
        container
        .use_case
        .confirm_replenishment_pick(
            data.get('sku'),
            data.get('batch_code'),
            data.get('quantity'),
        )
    )

    if res.is_success:
        return jsonify(
            res.value
        ), 200

    return jsonify({
        'error': res.error
    }), 400


@app.route('/api/putaway', methods=['POST'])
def putaway_stock():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    product_id = (
        data.get('sku')
        or data.get('id')
    )

    batch_code = data.get(
        'batch_code'
    )

    location_id = (
        data.get('location_id')
        or data.get('location')
    )

    res = container.use_case.execute_putaway(
        product_id,
        batch_code,
        location_id
    )

    if res.is_success:
        return jsonify({
            'message': 'Putaway registrado.'
        }), 200

    return jsonify({
        'error': res.error
    }), 400


@app.route('/api/stock/onboarding', methods=['POST'])
def onboard_existing_stock():
    """
    Incorpora ao controle do Kippe estoque que já existia
    fisicamente antes de sua entrada no sistema.

    Esta rota é semanticamente distinta de o fluxo de recebimento físico:
    ela nunca representa chegada física ocorrendo agora.
    """

    if not _has_valid_session():
        return jsonify({
            'error': (
                'Operador não autenticado.'
            )
        }), 401

    data = request.json or {}

    product_id = (
        data.get('sku')
        or data.get('id')
    )

    result = (
        container
        .existing_stock_onboarding_use_case
        .execute(
            product_id=product_id,
            quantity=data.get(
                'quantity'
            ),
            batch_code=data.get(
                'batch_code',
                '',
            ),
            expiration_date=data.get(
                'expiration_date',
                '',
            ),
            manufacturing_date=data.get(
                'manufacturing_date',
                '',
            ),
            supplier=data.get(
                'supplier',
                '',
            ),
            location_id=(
                data.get(
                    'location_id'
                )
                or data.get(
                    'location'
                )
                or ''
            ),
            historical_receipt_date=(
                data.get(
                    'historical_receipt_date'
                )
            ),
            historical_date_basis=(
                data.get(
                    'historical_date_basis'
                )
            ),
            document_id=data.get(
                'document_id',
                '',
            ),
        )
    )

    if result.is_success:
        onboarded = result.value

        return jsonify({
            'message': (
                'Estoque existente incorporado.'
            ),
            'onboarding': {
                'status': onboarded[
                    'status'
                ],
                'event_type': onboarded[
                    'event_type'
                ],
                'sku': onboarded[
                    'product_id'
                ],
                'batch_code': onboarded[
                    'batch_code'
                ],
                'quantity': onboarded[
                    'quantity'
                ],
                'quantity_before': onboarded[
                    'quantity_before'
                ],
                'quantity_after': onboarded[
                    'quantity_after'
                ],
                'location_id': onboarded[
                    'location_id'
                ],
                'supplier': onboarded[
                    'supplier'
                ],
                'document_id': onboarded[
                    'document_id'
                ],
                'historical_receipt_date': (
                    onboarded[
                        'historical_receipt_date'
                    ]
                ),
                'historical_date_basis': (
                    onboarded[
                        'historical_date_basis'
                    ]
                ),
            }
        }), 200

    error = str(
        result.error
        or 'Falha ao implantar estoque existente.'
    )

    normalized_error = (
        error.lower()
    )

    if (
        'sem privilégio'
        in normalized_error
        or 'sem privilegio'
        in normalized_error
        or 'autorização negada'
        in normalized_error
        or 'autorizacao negada'
        in normalized_error
    ):
        return jsonify({
            'error': error
        }), 403

    return jsonify({
        'error': error
    }), 400



def _build_supplier_invoice_reconciliation(data):
    """
    Shared NF documentary preparation authority.

    Used by both the read-only reconciliation endpoint and the certified
    physical receiving integration. It does not mutate stock.
    """
    if not isinstance(data, dict):
        raise ValueError(
            "Documento fiscal JSON obrigatório."
        )

    raw_lines = data.get("lines")

    if not isinstance(raw_lines, list):
        raise ValueError(
            "Linhas fiscais inválidas."
        )

    extracted_lines = [
        ExtractedInvoiceLineData(
            supplier_product_code=line.get(
                "supplier_product_code",
                "",
            ),
            description=line.get(
                "description",
                "",
            ),
            gtin=line.get(
                "gtin",
                "",
            ),
            commercial_unit=line.get(
                "commercial_unit",
                "",
            ),
            quantity=line.get(
                "quantity"
            ),
            unit_price=line.get(
                "unit_price"
            ),
        )
        for line in raw_lines
    ]

    extracted = ExtractedInvoiceData(
        invoice_number=data.get(
            "invoice_number",
            "",
        ),
        supplier_id=data.get(
            "supplier_id",
            "",
        ),
        access_key=data.get(
            "access_key",
            "",
        ),
        series=data.get(
            "series",
            "",
        ),
        origin_document=data.get(
            "origin_document",
            "MANUAL",
        ),
        lines=extracted_lines,
    )

    invoice = (
        container
        .invoice_preparation
        .prepare(extracted)
    )

    reconciliation = (
        container
        .invoice_reconciliation
        .reconcile(invoice)
    )

    return invoice, reconciliation


@app.route('/api/invoices/reconcile', methods=['POST'])
def reconcile_supplier_invoice():
    """
    Prepare ingestion-neutral fiscal evidence and reconcile it against the
    existing product catalog.

    This boundary is documentary/read-only with respect to stock.

    It deliberately does not:
    - create products;
    - receive goods;
    - mutate inventory quantities;
    - create batches;
    - perform putaway.
    """

    data = request.get_json(
        silent=True
    )

    if not isinstance(data, dict):
        return jsonify({
            'error': 'Documento fiscal JSON obrigatório.'
        }), 400

    raw_lines = data.get(
        'lines'
    )

    if not isinstance(raw_lines, list):
        return jsonify({
            'error': 'Linhas fiscais inválidas.'
        }), 400

    try:
        extracted_lines = [
            ExtractedInvoiceLineData(
                supplier_product_code=(
                    line.get(
                        'supplier_product_code',
                        ''
                    )
                ),
                description=line.get(
                    'description',
                    ''
                ),
                gtin=line.get(
                    'gtin',
                    ''
                ),
                commercial_unit=line.get(
                    'commercial_unit',
                    ''
                ),
                quantity=line.get(
                    'quantity'
                ),
                unit_price=line.get(
                    'unit_price'
                ),
            )
            for line in raw_lines
        ]

        extracted = ExtractedInvoiceData(
            invoice_number=data.get(
                'invoice_number',
                ''
            ),
            supplier_id=data.get(
                'supplier_id',
                ''
            ),
            access_key=data.get(
                'access_key',
                ''
            ),
            series=data.get(
                'series',
                ''
            ),
            origin_document=data.get(
                'origin_document',
                'MANUAL'
            ),
            lines=extracted_lines,
        )

        invoice = (
            container
            .invoice_preparation
            .prepare(
                extracted
            )
        )

        reconciliation = (
            container
            .invoice_reconciliation
            .reconcile(
                invoice
            )
        )

        unresolved = (
            container
            .unresolved_product
            .build(
                reconciliation
            )
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        return jsonify({
            'error': str(exc)
        }), 400

    pending_products = [
        {
            'invoice_number': pending.invoice_number,
            'supplier_id': pending.supplier_id,
            'supplier_product_code': (
                pending.supplier_product_code
            ),
            'description': pending.description,
            'gtin': pending.gtin,
            'commercial_unit': (
                pending.commercial_unit
            ),
            'quantity': pending.quantity,
            'reason': pending.reason.value,
        }
        for pending in unresolved.pending
    ]

    reconciled_lines = [
        {
            'supplier_product_code': (
                item.invoice_line
                .supplier_product_code
            ),
            'description': (
                item.invoice_line
                .description
            ),
            'gtin': item.invoice_line.gtin,
            'commercial_unit': (
                item.invoice_line
                .commercial_unit
            ),
            'quantity': (
                item.invoice_line
                .quantity
            ),
            'product_id': item.product_id,
            'status': item.status.value,
        }
        for item in reconciliation.lines
    ]

    return jsonify({
        'invoice_number': invoice.invoice_number,
        'supplier_id': invoice.supplier_id,
        'access_key': invoice.access_key,
        'series': invoice.series,
        'origin_document': (
            invoice.origin_document
        ),
        'total_lines': (
            reconciliation.total_lines
        ),
        'matched_lines': (
            reconciliation.matched_lines
        ),
        'needs_registration_lines': (
            reconciliation
            .needs_registration_lines
        ),
        'is_fully_reconciled': (
            reconciliation
            .is_fully_reconciled
        ),
        'lines': reconciled_lines,
        'pending_products': pending_products,
    }), 200


@app.route(
    '/api/invoices/receive-certified',
    methods=['POST'],
)
def receive_certified_supplier_invoice():
    """
    NF-001J.9 certified operator receiving boundary.

    Fiscal reconciliation remains documentary.
    Physical receiving occurs only after explicit conference evidence and
    always through J.8 SafeReceivingExecutionService.
    """
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.get_json(
        silent=True
    )

    if not isinstance(data, dict):
        return jsonify({
            'error': 'Documento fiscal JSON obrigatório.'
        }), 400

    invoice_payload = data.get(
        'invoice'
    )

    conference_payload = data.get(
        'conference'
    )

    if not isinstance(
        invoice_payload,
        dict,
    ):
        return jsonify({
            'error': 'invoice é obrigatório.'
        }), 400

    if not isinstance(
        conference_payload,
        dict,
    ):
        return jsonify({
            'error': 'conference é obrigatório.'
        }), 400

    operator_id = (
        request.headers.get(
            'X-Test-Operator-Override'
        )
        if (
            container.config.ENV == 'testing'
            and 'X-Test-Operator-Override'
            in request.headers
        )
        else session.get(
            'operator_id'
        )
    )

    raw_counts = conference_payload.get(
        'counts',
        {}
    )

    raw_physical = conference_payload.get(
        'physical_data',
        {}
    )

    if not isinstance(raw_counts, dict):
        return jsonify({
            'error': 'conference.counts inválido.'
        }), 400

    if not isinstance(raw_physical, dict):
        return jsonify({
            'error': 'conference.physical_data inválido.'
        }), 400

    try:
        counts = {
            int(key): value
            for key, value in raw_counts.items()
        }

        physical_data = {
            int(key): value
            for key, value in raw_physical.items()
        }

        _, reconciliation = (
            _build_supplier_invoice_reconciliation(
                invoice_payload
            )
        )

        result = (
            OperatorReceivingIntegrationService
            .execute(
                repository=(
                    container.product_repository
                ),
                reconciliation=reconciliation,
                operator_id=operator_id,
                counts=counts,
                physical_data=physical_data,
            )
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        return jsonify({
            'error': str(exc)
        }), 400

    return jsonify({
        'message': (
            'Conferência e recebimento certificados processados.'
        ),
        'invoice_number': result.invoice_number,
        'supplier_id': result.supplier_id,
        'conference_closed_by': (
            result.conference_closed_by
        ),
        'total_lines': result.total_lines,
        'divergent_lines': result.divergent_lines,
        'executed_lines': result.executed_lines,
        'replay_lines': result.replay_lines,
        'skipped_zero_quantity_lines': (
            result.skipped_zero_quantity_lines
        ),
        'lines': [
            {
                'line_number': line.line_number,
                'product_id': line.product_id,
                'status': line.status,
                'executed': line.executed,
                'operation_status': (
                    line.operation_status
                ),
                'audit_event_id': (
                    line.audit_event_id
                ),
            }
            for line in result.lines
        ],
    }), 200


@app.route('/api/receive', methods=['POST'])
def receive_stock():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    product_id = (
        data.get('sku')
        or data.get('id')
    )

    amount = (
        data.get('quantity')
        or data.get('amount')
    )

    manufacturing_date = data.get(
        'manufacturing_date',
        ''
    )

    invoice_id = data.get(
        'invoice_id',
        ''
    )

    origin_document = data.get(
        'origin_document',
        'MANUAL'
    )

    operator_id = (
        request.headers.get(
            'X-Test-Operator-Override'
        )
        if (
            container.config.ENV == 'testing'
            and 'X-Test-Operator-Override'
            in request.headers
        )
        else session.get(
            'operator_id'
        )
    )

    res = container.receive_use_case.execute(
        identifier=product_id,
        quantity=amount,
        batch_code=data.get(
            'batch_code',
            ''
        ),
        expiration_date=data.get(
            'expiration_date',
            ''
        ),
        supplier=data.get(
            'supplier',
            'PADRAO'
        ),
        manufacturing_date=(
            manufacturing_date
        ),
        invoice_id=invoice_id,
        origin_document=origin_document,
        operator_id=operator_id,
    )

    if res.is_success:
        received = res.value

        return jsonify({
            'message': 'Entrada registrada.',
            'receiving': {
                'sku': (
                    received[
                        'product_id'
                    ]
                ),
                'batch_code': (
                    received[
                        'batch_code'
                    ]
                ),
                'quantity': (
                    received[
                        'quantity'
                    ]
                ),
                'supplier': (
                    received[
                        'supplier'
                    ]
                ),
                'manufacturing_date': (
                    received[
                        'manufacturing_date'
                    ]
                ),
                'expiration_date': (
                    received[
                        'expiration_date'
                    ]
                ),
                'invoice_id': (
                    invoice_id
                ),
                'origin_document': (
                    origin_document
                ),
                'putaway_status': (
                    'PENDENTE'
                ),
            }
        }), 200

    return jsonify({
        'error': res.error
    }), 400


@app.route('/api/entrada', methods=['POST'])
def add_stock():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    res = container.use_case.execute_add(
        data.get('id'),
        data.get('amount'),
        data.get(
            'expiration_date',
            ''
        ),
        data.get(
            'batch_code',
            ''
        ),
        data.get(
            'manufacturing_date',
            ''
        ),
        data.get(
            'supplier',
            'PADRAO'
        )
    )

    if res.is_success:
        return jsonify({
            'message': 'OK'
        }), 200

    return jsonify({
        'error': res.error
    }), 400


@app.route('/api/saida', methods=['POST'])
def remove_stock():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    res = container.use_case.execute_remove(
        data.get('id'),
        data.get('amount')
    )

    if res.is_success:
        return jsonify({
            'message': 'OK'
        }), 200

    return jsonify({
        'error': res.error
    }), 400


@app.route('/api/historico', methods=['GET'])
def get_historico():
    return jsonify(
        container.use_case.get_recent_history()
    )


def _document_operator_id():
    if (
        container.config.ENV == 'testing'
        and 'X-Test-Operator-Override' in request.headers
    ):
        return request.headers.get(
            'X-Test-Operator-Override'
        )

    return session.get(
        'operator_id'
    )


# ========================================================
# NF-001K.3 — DANFE HTTP ACQUISITION GATEWAY
# ========================================================

@app.route(
    '/api/invoices/danfe/acquire',
    methods=['POST']
)
def acquire_danfe_document():
    """
    Acquire authenticated DANFE image evidence.

    This boundary performs acquisition only. It does not perform OCR,
    reconciliation, receiving, product registration or stock mutation.
    """
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    uploaded_file = request.files.get(
        'file'
    )

    if (
        uploaded_file is None
        or not uploaded_file.filename
    ):
        return jsonify({
            'error': 'Arquivo obrigatório.'
        }), 400

    operator_id = _document_operator_id()

    if not operator_id:
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    from datetime import datetime, timezone

    acquired_at = (
        datetime.now(timezone.utc)
        .astimezone()
        .isoformat()
    )

    try:
        result = (
            DanfeHttpAcquisitionService()
            .acquire(
                uploaded_file=uploaded_file,
                operator_id=str(operator_id),
                acquired_at=acquired_at,
            )
        )

    except DanfeHttpAcquisitionError as exc:
        return jsonify({
            'error': str(exc)
        }), 400

    except ValueError as exc:
        return jsonify({
            'error': str(exc)
        }), 400

    return jsonify({
        'document_sha256': result.document_sha256,
        'filename': result.filename,
        'mime_type': result.mime_type,
        'size_bytes': result.size_bytes,
        'source': result.source,
        'acquired_at': (
            result.document
            .metadata
            .acquired_at
        ),
    }), 201


# ========================================================
# DOCUMENT-001D — DOCUMENT ATTACHMENT HTTP GATEWAY
# ========================================================



@app.route(
    '/api/audit-events/<int:event_id>/attachments',
    methods=['POST']
)
def attach_document_to_audit_event(event_id):
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    uploaded_file = request.files.get(
        'file'
    )

    if (
        uploaded_file is None
        or not uploaded_file.filename
    ):
        return jsonify({
            'error': 'Arquivo obrigatório.'
        }), 400

    operator_id = _document_operator_id()

    if not operator_id:
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    try:
        result = (
            container
            .document_attachment_use_case
            .attach(
                event_id=event_id,
                content=uploaded_file.read(),
                original_filename=(
                    uploaded_file.filename
                ),
                declared_mime_type=(
                    uploaded_file.mimetype
                ),
                business_document_number=(
                    request.form.get(
                        'business_document_number',
                        ''
                    )
                ),
                supplier=(
                    request.form.get(
                        'supplier',
                        ''
                    )
                ),
                operator_id=str(
                    operator_id
                ),
            )
        )

    except ValueError as exc:
        return jsonify({
            'error': str(exc)
        }), 400

    except Exception as exc:
        return jsonify({
            'error': str(exc)
        }), 400

    return jsonify(
        result
    ), 201


@app.route(
    '/api/document-attachments/<attachment_id>',
    methods=['GET']
)
def get_document_attachment_metadata(
    attachment_id
):
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    metadata = (
        container
        .product_repository
        .get_document_attachment(
            attachment_id
        )
    )

    if metadata is None:
        return jsonify({
            'error': 'Documento não encontrado.'
        }), 404

    return jsonify(
        metadata
    ), 200


@app.route(
    '/api/document-attachments/<attachment_id>/content',
    methods=['GET']
)
def get_document_attachment_content(
    attachment_id
):
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    metadata = (
        container
        .product_repository
        .get_document_attachment(
            attachment_id
        )
    )

    if metadata is None:
        return jsonify({
            'error': 'Documento não encontrado.'
        }), 404

    try:
        document_path = (
            container
            .document_storage
            .resolve(
                metadata[
                    'relative_path'
                ]
            )
        )

    except Exception as exc:
        return jsonify({
            'error': str(exc)
        }), 400

    if (
        not document_path.exists()
        or not document_path.is_file()
    ):
        return jsonify({
            'error': 'Conteúdo documental não encontrado.'
        }), 404

    return send_file(
        document_path,
        mimetype=metadata[
            'mime_type'
        ],
        as_attachment=False,
        download_name=metadata[
            'original_filename'
        ],
    )


@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('web/css', filename)


@app.route('/vendor/<path:filename>')
def serve_vendor(filename):
    return send_from_directory('web/vendor', filename)


@app.route('/icons/<path:filename>')
def serve_icons(filename):
    return send_from_directory('web/icons', filename)



def _check_invoice_duplicate_records(supplier: str, invoice_number: str) -> dict:
    inv = str(invoice_number or '').strip()
    if not inv:
        return {'duplicate': False}

    sup_norm = _norm_catalog_text(supplier)
    conn = _get_kippe_db()
    try:
        row_log = conn.execute(
            '''
            SELECT invoice_number, COUNT(*) AS lines, SUM(quantity) AS total_qty, MAX(created_at) AS last_at
            FROM conference_audit_log
            WHERE invoice_number = ? AND (? = '' OR supplier_norm = ?)
            GROUP BY invoice_number
            LIMIT 1
            ''',
            (inv, sup_norm, sup_norm),
        ).fetchone()
        if row_log:
            return {
                'duplicate': True,
                'source': 'ESTOQUE_EFETIVADO',
                'invoice_number': inv,
                'lines': int(row_log['lines'] or 0),
                'total_qty': int(row_log['total_qty'] or 0),
                'last_at': str(row_log['last_at'] or '')[:16].replace('T', ' '),
                'message': f"A NF {inv} já foi efetivada no estoque em {str(row_log['last_at'] or '')[:10]} ({int(row_log['total_qty'] or 0)} un).",
            }

        pending_rows = conn.execute(
            "SELECT id, supplier, invoice_number, submitted_by_name, created_at FROM receiving_pending_queue WHERE status = 'PENDENTE'"
        ).fetchall()
        for pr in pending_rows:
            pr_sup_norm = _norm_catalog_text(pr['supplier'] or '')
            if sup_norm and pr_sup_norm and pr_sup_norm != sup_norm:
                continue
            pr_invs = [x.strip() for x in str(pr['invoice_number'] or '').split(',') if x.strip()]
            if inv in pr_invs:
                return {
                    'duplicate': True,
                    'source': 'FILA_PENDENTE',
                    'invoice_number': inv,
                    'queue_id': int(pr['id']),
                    'message': f"A NF {inv} já está aguardando armazenagem na fila (#{pr['id']}) enviada por {pr['submitted_by_name']}.",
                }
    finally:
        conn.close()

    return {'duplicate': False}


def _persist_receiving_divergences(
    supplier: str,
    default_invoice: str,
    divergences: list,
    op_id: str,
    op_name: str,
) -> int:
    if not divergences or not isinstance(divergences, list):
        return 0

    now_iso = __import__('datetime').datetime.now().isoformat(timespec='seconds')
    sup_clean = str(supplier or 'PADRAO').strip().upper()
    sup_norm = _norm_catalog_text(sup_clean)
    saved_count = 0

    conn = _get_kippe_db()
    try:
        for d in divergences:
            if not isinstance(d, dict):
                continue
            exp_q = int(d.get('expected_qty') or 0)
            cnt_q = int(d.get('counted_qty') or 0)
            diff_q = cnt_q - exp_q
            if diff_q == 0:
                continue
            inv_num = str(d.get('invoice_number') or default_invoice or 'S/N').strip()
            sku = str(d.get('sku') or '').strip()
            pname = str(d.get('name') or sku).strip()
            reason = str(d.get('reason') or 'DIVERGENCIA_NAO_ESPECIFICADA').strip().upper()
            notes = str(d.get('notes') or '').strip()

            conn.execute(
                '''
                INSERT INTO receiving_divergences (
                    supplier, supplier_norm, invoice_number, sku, product_name,
                    expected_qty, counted_qty, divergence_qty, reason, notes,
                    operator_id, operator_name, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    sup_clean, sup_norm, inv_num, sku, pname,
                    exp_q, cnt_q, diff_q, reason, notes,
                    op_id or 'SYSTEM', op_name or op_id or 'SYSTEM', now_iso,
                ),
            )
            saved_count += 1
        conn.commit()
    finally:
        conn.close()

    if saved_count > 0:
        _record_audit_event(
            "DIVERGENCE_RECORDED",
            "RECEBIMENTO",
            f"Registradas {saved_count} divergência(s) na conferência · {sup_clean} · NF {default_invoice or 'MULTI'}",
            target_ref=f"NF-{default_invoice or 'MULTI'}",
        )
    return saved_count


def _expand_multinf_allocations(items: list, default_invoice: str) -> list:
    expanded = []
    for item in items:
        allocs = item.get('nf_allocations')
        total_qty = int(item.get('quantity') or item.get('scanned') or 0)
        if not allocs or not isinstance(allocs, list) or len(allocs) <= 1 or total_qty <= 0:
            copy_it = dict(item)
            if not copy_it.get('invoice_number') and allocs and len(allocs) == 1:
                copy_it['invoice_number'] = str(allocs[0].get('invoice_number') or default_invoice).strip()
            expanded.append(copy_it)
            continue

        remaining = total_qty
        for idx, alloc in enumerate(allocs):
            inv_num = str(alloc.get('invoice_number') or default_invoice).strip()
            exp_units = max(0, int(alloc.get('expected_units') or 0))
            is_last = (idx == len(allocs) - 1)
            if is_last:
                alloc_qty = remaining
            else:
                alloc_qty = min(remaining, exp_units) if exp_units > 0 else 0
            remaining = max(0, remaining - alloc_qty)
            if alloc_qty > 0:
                sub_it = dict(item)
                sub_it['quantity'] = alloc_qty
                sub_it['invoice_number'] = inv_num
                expanded.append(sub_it)

    return expanded


@app.route('/api/invoices/check-duplicate', methods=['POST'])
def check_invoice_duplicate_api():
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    data = request.json or {}
    supplier = str(data.get('supplier') or '').strip()
    invoice_number = str(data.get('invoice_number') or '').strip()
    info = _check_invoice_duplicate_records(supplier, invoice_number)
    return jsonify(info), 200


@app.route('/api/conference/finalize', methods=['POST'])
def conference_finalize():
    """
    Finaliza conferência e dá entrada direta no estoque.
    Fluxo simplificado para conferente: apenas SKU + quantidade + lote + validade.
    """
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    data = request.json or {}
    items = data.get('items', [])
    ctx_supplier = str(data.get('supplier') or '').strip()
    ctx_invoice = str(data.get('invoice_number') or '').strip()

    if not items or not isinstance(items, list):
        return jsonify({'error': 'Nenhum item para finalizar.'}), 400

    op_id, op_name, op_role = _get_active_operator_context()
    op_id = op_id or 'SYSTEM'
    force_duplicate = bool(data.get('force', False))
    divergences_payload = data.get('divergences') or []
    invoice_list = [str(x).strip() for x in (data.get('invoices') or []) if str(x).strip()]
    if not invoice_list and ctx_invoice:
        invoice_list = [x.strip() for x in ctx_invoice.split(',') if x.strip()]

    if invoice_list and not force_duplicate:
        for inv_chk in invoice_list:
            dup_info = _check_invoice_duplicate_records(ctx_supplier, inv_chk)
            if dup_info.get('duplicate'):
                return jsonify({
                    'duplicate': True,
                    'duplicate_invoice': inv_chk,
                    'error': dup_info.get('message') or f"A NF {inv_chk} já foi registrada anteriormente.",
                }), 409

    expanded_items = _expand_multinf_allocations(items, ctx_invoice)
    combined_invoice_label = ", ".join(invoice_list) if invoice_list else ctx_invoice
    has_unlinked = any(
        not str(it.get('sku') or '').strip() or str(it.get('sku') or '').strip().startswith('TEMP-')
        for it in expanded_items
    )

    if AccessControl.is_conference_only(op_role) or has_unlinked:
        div_saved = _persist_receiving_divergences(
            supplier=ctx_supplier,
            default_invoice=combined_invoice_label,
            divergences=divergences_payload,
            op_id=op_id,
            op_name=op_name,
        )
        now_iso = __import__('datetime').datetime.now().isoformat(timespec='seconds')
        conn_q = _get_kippe_db()
        try:
            cur_q = conn_q.execute(
                '''
                INSERT INTO receiving_pending_queue (
                    supplier, invoice_number, submitted_by_id, submitted_by_name,
                    status, items_json, created_at
                ) VALUES (?, ?, ?, ?, 'PENDENTE', ?, ?)
                ''',
                (
                    ctx_supplier or 'PADRAO',
                    combined_invoice_label,
                    op_id,
                    op_name,
                    json.dumps(expanded_items, ensure_ascii=False),
                    now_iso,
                ),
            )
            conn_q.commit()
            q_id = int(cur_q.lastrowid)
        finally:
            conn_q.close()

        _record_audit_event(
            "CONFERENCE_QUEUED",
            "RECEBIMENTO",
            f"Conferência enviada para armazenagem: {ctx_supplier or 'PADRAO'} · NF {combined_invoice_label or 'S/N'} ({len(expanded_items)} lançamentos)",
            target_ref=f"NF-{combined_invoice_label or q_id}",
        )
        return jsonify({
            'queued': True,
            'queue_id': q_id,
            'submitted_items': len(expanded_items),
            'divergences_recorded': div_saved,
            'message': 'Conferência enviada para cadastro/armazenagem do Estoquista.',
        }), 202

    if AccessControl.is_conference_only(op_role):
        now_iso = __import__('datetime').datetime.now().isoformat(timespec='seconds')
        conn_q = _get_kippe_db()
        try:
            cur_q = conn_q.execute(
                '''
                INSERT INTO receiving_pending_queue (
                    supplier, invoice_number, submitted_by_id, submitted_by_name,
                    status, items_json, created_at
                ) VALUES (?, ?, ?, ?, 'PENDENTE', ?, ?)
                ''',
                (
                    ctx_supplier or 'PADRAO',
                    ctx_invoice,
                    op_id,
                    op_name,
                    json.dumps(items, ensure_ascii=False),
                    now_iso,
                ),
            )
            conn_q.commit()
            q_id = int(cur_q.lastrowid)
        finally:
            conn_q.close()

        _record_audit_event(
            "CONFERENCE_QUEUED",
            "RECEBIMENTO",
            f"Conferência enviada para armazenagem: {ctx_supplier or 'PADRAO'} · NF {ctx_invoice or 'S/N'} ({len(items)} itens)",
            target_ref=f"NF-{ctx_invoice or q_id}",
        )
        return jsonify({
            'queued': True,
            'queue_id': q_id,
            'submitted_items': len(items),
            'message': 'Conferência enviada para cadastro/armazenagem do Estoquista.',
        }), 202
    
    force_duplicate = bool(data.get('force', False))
    if ctx_invoice and not force_duplicate:
        try:
            conn_chk = _get_kippe_db()
            sup_norm_chk = _norm_catalog_text(ctx_supplier)
            skus_chk = [str(it.get('sku') or '').strip() for it in items if it.get('sku')]
            dups = []
            for s_chk in skus_chk:
                row_dup = conn_chk.execute(
                    "SELECT sku, quantity, created_at FROM conference_audit_log WHERE invoice_number = ? AND sku = ? AND (? = '' OR supplier_norm = ?) LIMIT 1",
                    (ctx_invoice, s_chk, sup_norm_chk, sup_norm_chk)
                ).fetchone()
                if row_dup:
                    dups.append(f"{row_dup['sku']} ({row_dup['quantity']} UN em {row_dup['created_at'][:10]})")
            conn_chk.close()
            if dups:
                return jsonify({
                    'duplicate': True,
                    'error': f"A NF {ctx_invoice} já possui lançamento registrado para: {', '.join(dups)}. Deseja lançar novamente?"
                }), 409
        except Exception:
            pass

    results = []
    errors = []
    
    for item in expanded_items:
        sku = str(item.get('sku') or '').strip()
        quantity = item.get('quantity', 0)
        batch_code = str(item.get('batch_code') or '').strip() or f"LOTE-{__import__('datetime').date.today().isoformat().replace('-', '')}"
        expiration_date = str(item.get('expiration_date') or '').strip()
        manufacturing_date = str(item.get('manufacturing_date') or '').strip()
        supplier = str(item.get('supplier') or ctx_supplier or 'PADRAO').strip()
        item_invoice = str(item.get('invoice_number') or combined_invoice_label or '').strip()
        
        if not sku:
            errors.append({'sku': None, 'error': 'SKU vazio'})
            continue
        if not isinstance(quantity, int) or quantity <= 0:
            errors.append({'sku': sku, 'error': f'Quantidade inválida: {quantity}'})
            continue
        if not expiration_date:
            errors.append({'sku': sku, 'error': 'Data de validade obrigatória'})
            continue
        
        # Busca produto
        product = container.product_repository.get_by_id(sku)
        if not product:
            errors.append({'sku': sku, 'error': 'Produto não cadastrado'})
            continue
        
        # Chama o use case padrão de entrada
        try:
            result = container.receive_use_case.execute(
                identifier=sku,
                quantity=quantity,
                batch_code=batch_code,
                expiration_date=expiration_date,
                supplier=supplier,
                manufacturing_date=manufacturing_date,
                origin_document=item_invoice if item_invoice else 'CONFERENCE',
                operator_id=op_id,
            )
            if result.is_success:
                results.append({'sku': sku, 'quantity': quantity, 'batch_code': batch_code})
                try:
                    conn_log = _get_kippe_db()
                    conn_log.execute(
                        "INSERT INTO conference_audit_log (supplier_norm, invoice_number, sku, quantity, batch_code, expiration_date, operator_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (_norm_catalog_text(supplier), item_invoice, sku, quantity, batch_code, expiration_date, op_id, __import__('datetime').datetime.now().isoformat(timespec='seconds'))
                    )
                    conn_log.commit()
                    conn_log.close()
                except Exception:
                    pass
            else:
                errors.append({'sku': sku, 'error': str(result.error)})
        except Exception as exc:
            errors.append({'sku': sku, 'error': str(exc)})
    
    div_saved = _persist_receiving_divergences(
        supplier=ctx_supplier,
        default_invoice=combined_invoice_label,
        divergences=divergences_payload,
        op_id=op_id,
        op_name=op_name,
    )
    return jsonify({
        'success': len(results),
        'failed': len(errors),
        'divergences_recorded': div_saved,
        'results': results,
        'errors': errors,
    }), 200 if not errors else 207



SHARE_TMP_DIR = Path(tempfile.gettempdir()) / "kippe_shares"
SHARE_TMP_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_ocr_json_payload(parsed):
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list):
        if len(parsed) == 1 and isinstance(parsed[0], dict):
            return parsed[0]
        dict_items = [x for x in parsed if isinstance(x, dict)]
        if dict_items:
            first = dict_items[0]
            if "items" in first or "supplier" in first or "invoice_number" in first:
                merged_items = []
                sup = ""
                inv = ""
                for obj in dict_items:
                    if not sup and obj.get("supplier"):
                        sup = obj.get("supplier")
                    if not inv and obj.get("invoice_number"):
                        inv = obj.get("invoice_number")
                    if isinstance(obj.get("items"), list):
                        merged_items.extend(obj["items"])
                return {"supplier": sup, "invoice_number": inv, "items": merged_items}
            return {"supplier": "", "invoice_number": "", "items": dict_items}
    return {"supplier": "", "invoice_number": "", "items": []}


def _call_gemini_fast(
    api_key: str,
    media_b64: str,
    page_num: int = 1,
    total_pages: int = 1,
    mime_type: str = "image/jpeg",
) -> dict:
    if mime_type == "application/pdf":
        page_hint = (
            "Este é o arquivo PDF completo da Nota Fiscal (pode conter 1 ou mais páginas). "
            "Extraia o fornecedor, o número da NF e todos os itens da tabela de produtos de todas as páginas."
        )
    else:
        page_hint = (
            f"Esta é a PÁGINA {page_num} de {total_pages} do documento. "
            + (
                "Se for página de continuação (página 2 ou posterior), extraia todos os itens da tabela desta página "
                "(se o cabeçalho do fornecedor ou número da NF não aparecer aqui, retorne strings vazias nesses campos)."
                if page_num > 1 else
                "Extraia o fornecedor, o número da NF e todos os itens da tabela desta primeira página."
            )
        )

    prompt = (
        "Você está extraindo dados de uma tabela de Nota Fiscal (DANFE retrato/paisagem, NFC-e ou romaneio). "
        f"{page_hint}\n"
        "PRIVACIDADE LGPD: Ignore completamente o quadro 'DESTINATÁRIO / REMETENTE' (supermercado cliente), CNPJs, CPFs, "
        "chave de acesso, impostos e totais gerais da nota.\n\n"
        "REGRAS RÍGIDAS DE LEITURA DA TABELA DE PRODUTOS (LEIA LINHA POR LINHA HORIZONTALMENTE):\n"
        "- Cada linha da tabela tem colunas como: CÓD | DESCRIÇÃO | NCM | CST | CFOP | UN | QUANT. | V.UNIT | V.TOTAL.\n"
        "- NUNCA misture a quantidade, unidade ou embalagem de uma linha com a linha de cima ou de baixo.\n"
        "- Confira mentalmente se QUANT. × V.UNIT ≈ V.TOTAL da mesma linha.\n"
        "- 'description': Copie a descrição INTEIRA da coluna DESCRIÇÃO desde a PRIMEIRA letra até a última (NUNCA corte o início como 'IOGURTE', 'IOG.', 'LEITE', 'QUEIJO'), MANTENDO OBRIGATORIAMENTE gramatura, volume e multiplicador de caixa "
        "(ex: 'MILHO CONSERVA 24X170G LATA STELLA DORO', 'BACON PALETA COM PELE FREE CARNE APX.11KG COD.251').\n"
        "- 'unit': Sigla exata da coluna UN / UNID daquela linha (ex: 'KG', 'CX', 'FD', 'UN', 'PCT', 'LT').\n"
        "- 'quantity': Número exato da coluna QUANT. / QTD daquela linha (mantenha decimais se houver, ex: 11.0 ou 11.45).\n"
        "- 'pack_factor': Número inteiro de unidades dentro da caixa/fardo indicado na própria descrição da linha "
        "(ex: '24X170G' -> 24, '16X1.01KG' -> 16, 'CX C/ 12' -> 12). "
        "ATENÇÃO A PRODUTOS NO KG (AÇOUGUE / FRIOS / CONGELADOS): Se a coluna UN for 'KG' ou a descrição indicar peso aproximado por peça/caixa "
        "(ex: 'APX.11KG', 'PESO VARIAVEL'), use 'pack_factor': 1. NUNCA confunda o peso '11KG' com 11 unidades.\n\n"
        "Extraia também:\n"
        "- 'supplier': Nome do FORNECEDOR / EMITENTE no topo da nota.\n"
        "- 'invoice_number': Número da NF-e / DANFE próximo a 'Nº' e 'SÉRIE' (apenas dígitos, sem CEP/telefone/página).\n\n"
        "Retorne SOMENTE JSON válido: "
        '{"supplier": "NOME DO FORNECEDOR", "invoice_number": "123456", "items": [{"description": "DESCRICAO COMPLETA", "unit": "UN", "quantity": 1, "pack_factor": 1}]}'
    )

    attempts = [
        ("gemini-3.8-flash", None),
        ("gemini-3-flash-preview", {"thinkingLevel": "low"}),
        ("gemini-flash-lite-latest", None),
    ]

    last_err = None
    saw_overload = False

    for attempt_idx, (model_name, t_cfg) in enumerate(attempts):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        gen_cfg = {
            "responseMimeType": "application/json",
            "temperature": 0.0,
            "maxOutputTokens": 4096,
        }
        if t_cfg is not None:
            gen_cfg["thinkingConfig"] = t_cfg

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": media_b64}}
                ]
            }],
            "generationConfig": gen_cfg,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=24) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            texto = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            return _normalize_ocr_json_payload(json.loads(texto))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            last_err = RuntimeError(f"Erro API Google ({e.code}): {err_body}")
            if e.code in (429, 503):
                saw_overload = True
                time.sleep(min(4.0, 1.2 * (attempt_idx + 1)))
                continue
            if e.code in (400, 404):
                continue
            raise last_err
        except (TimeoutError, urllib.error.URLError) as e:
            last_err = RuntimeError(f"Timeout/Rede em {model_name}: {e}")
            time.sleep(1.0)
            continue

    secondary_res, secondary_diag = _try_secondary_vision_providers(prompt, media_b64, mime_type)
    if isinstance(secondary_res, dict) and ("items" in secondary_res or "supplier" in secondary_res):
        return secondary_res

    extra = f" | Fallback: {secondary_diag}" if secondary_diag else ""
    if saw_overload:
        raise RuntimeError(f"Gemini congestionado (503){extra}. Suas fotos foram preservadas — tente novamente ou siga em Conferência Cega.")
    if last_err:
        raise RuntimeError(f"{last_err}{extra}")
    raise RuntimeError("Não foi possível obter resposta da API Gemini.")



def _call_openai_compatible_vision(
    provider_name: str,
    endpoint_url: str,
    api_key: str,
    model_name: str,
    prompt: str,
    media_b64: str,
    mime_type: str,
) -> dict:
    payload = {
        "model": model_name,
        "temperature": 0.0,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{media_b64}"}},
            ],
        }],
    }
    req = urllib.request.Request(
        endpoint_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "KippeWMS/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=22) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as he:
        body = he.read().decode("utf-8", errors="ignore")[:180]
        raise RuntimeError(f"{provider_name} HTTP {he.code}: {body}")
    texto = result["choices"][0]["message"]["content"].strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto, flags=re.IGNORECASE).strip()
    return _normalize_ocr_json_payload(json.loads(texto))


def _try_secondary_vision_providers(prompt: str, media_b64: str, mime_type: str):
    if mime_type == "application/pdf":
        return None, "PDF nativo suportado apenas no provedor principal"

    diag_notes = []
    groq_key = (os.getenv("GROQ_API_KEY") or "").strip()
    if groq_key:
        for g_model in ("meta-llama/llama-4-maverick-17b-128e-instruct", "meta-llama/llama-4-scout-17b-16e-instruct"):
            try:
                res = _call_openai_compatible_vision(
                    "Groq",
                    "https://api.groq.com/openai/v1/chat/completions",
                    groq_key,
                    g_model,
                    prompt,
                    media_b64,
                    mime_type,
                )
                return res, None
            except Exception as exc:
                diag_notes.append(str(exc))
                continue
    else:
        diag_notes.append("GROQ_API_KEY não detectada no servidor")

    mistral_key = (os.getenv("MISTRAL_API_KEY") or "").strip()
    if mistral_key:
        try:
            res = _call_openai_compatible_vision(
                "Mistral",
                "https://api.mistral.ai/v1/chat/completions",
                mistral_key,
                "pixtral-12b-2409",
                prompt,
                media_b64,
                mime_type,
            )
            return res, None
        except Exception as exc:
            diag_notes.append(str(exc))

    return None, " | ".join(diag_notes)


def _prepare_page_b64(img: Image.Image, is_last_page: bool = True) -> str:
    """Prepara uma pagina da DANFE para envio a IA com orientacao EXIF corrigida, alta nitidez e LGPD."""
    from PIL import ImageEnhance
    image = ImageOps.exif_transpose(img).convert('L')
    width, height = image.size

    if height >= width:
        cut_ratio = 0.90 if is_last_page else 0.97
        bottom_cut = int(height * cut_ratio)
        if bottom_cut > 200:
            image = image.crop((0, 0, width, bottom_cut))

    draw = ImageDraw.Draw(image)
    w_now, h_now = image.size
    if h_now >= w_now:
        top_band_top = int(h_now * 0.015)
        top_band_bottom = int(h_now * 0.075)
        if top_band_bottom > top_band_top + 10:
            draw.rectangle(
                [(int(w_now * 0.55), top_band_top), (w_now, top_band_bottom)],
                fill=0,
            )

    image = ImageOps.autocontrast(image, cutoff=0.5)
    image = ImageEnhance.Sharpness(image).enhance(1.35)
    resample_filter = getattr(Image, 'Resampling', Image).LANCZOS
    image.thumbnail((2200, 2200), resample_filter)

    buf = io.BytesIO()
    image.save(buf, format='JPEG', quality=88, optimize=True)
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def _strip_pdf_header_noise(pdf_bytes: bytes) -> bytes:
    idx = pdf_bytes.find(b'%PDF-')
    if 0 < idx <= 2048:
        return pdf_bytes[idx:]
    return pdf_bytes


def _repair_pdf_xref_python(pdf_bytes: bytes) -> bytes:
    pdf_bytes = _strip_pdf_header_noise(pdf_bytes)
    obj_matches = list(re.finditer(rb'(?:^|[\r\n])\s*(\d+)\s+(\d+)\s+obj\b', pdf_bytes))
    if not obj_matches:
        return b""

    offsets = {}
    for m in obj_matches:
        obj_num = int(m.group(1))
        gen_num = int(m.group(2))
        offsets[obj_num] = (m.start(1), gen_num)

    max_obj = max(offsets.keys())
    new_size = max_obj + 1

    trailer_dict = b""
    trailer_matches = list(re.finditer(rb'trailer\s*(<<.*?>>)', pdf_bytes, re.DOTALL))
    if trailer_matches:
        trailer_dict = trailer_matches[-1].group(1)
    else:
        xref_stm = list(re.finditer(rb'<<[^>]*?/Type\s*/XRef[^>]*?>>', pdf_bytes, re.DOTALL))
        if xref_stm:
            raw_d = xref_stm[-1].group(0)
            for tag in [rb'/Type\s*/XRef', rb'/W\s*\[[^\]]*\]', rb'/Index\s*\[[^\]]*\]', rb'/Filter\s*/\w+', rb'/DecodeParms\s*<<.*?>>', rb'/Length\s*\d+']:
                raw_d = re.sub(tag, b'', raw_d, flags=re.DOTALL)
            trailer_dict = raw_d

    if not trailer_dict:
        return b""

    if re.search(rb'/Size\s+\d+', trailer_dict):
        trailer_dict = re.sub(rb'/Size\s+\d+', f'/Size {new_size}'.encode('ascii'), trailer_dict, count=1)
    else:
        trailer_dict = trailer_dict[:-2] + f' /Size {new_size} >>'.encode('ascii')

    trailer_dict = re.sub(rb'/Prev\s+\d+', b'', trailer_dict)

    xref_lines = [f"xref\r\n0 {new_size}\r\n".encode('ascii'), b"0000000000 65535 f \r\n"]
    for i in range(1, new_size):
        if i in offsets:
            off, gen = offsets[i]
            xref_lines.append(f"{off:010d} {gen:05d} n \r\n".encode('ascii'))
        else:
            xref_lines.append(b"0000000000 65535 f \r\n")

    base = pdf_bytes.rstrip() + b"\r\n"
    xref_offset = len(base)
    return (
        base
        + b"".join(xref_lines)
        + b"trailer\r\n"
        + trailer_dict
        + f"\r\nstartxref\r\n{xref_offset}\r\n%%EOF\r\n".encode('ascii')
    )


def _extract_embedded_jpegs_from_pdf(pdf_bytes: bytes) -> list:
    images = []
    pos = 0
    total_len = len(pdf_bytes)
    while len(images) < 8 and pos < total_len:
        start = pdf_bytes.find(b'\xff\xd8\xff', pos)
        if start == -1:
            break
        endstream_pos = pdf_bytes.find(b'endstream', start + 3)
        if endstream_pos != -1:
            eoi = pdf_bytes.rfind(b'\xff\xd9', start + 3, endstream_pos)
            next_pos = endstream_pos + 9
        else:
            eoi = pdf_bytes.rfind(b'\xff\xd9', start + 3)
            next_pos = (eoi + 2) if eoi != -1 else total_len

        if eoi == -1:
            pos = start + 3
            continue

        chunk = pdf_bytes[start:eoi + 2]
        pos = max(next_pos, eoi + 2)
        if len(chunk) < 4000:
            continue
        try:
            im = Image.open(io.BytesIO(chunk))
            im.load()
            if im.width >= 400 and im.height >= 400:
                images.append(im)
        except Exception:
            continue
    return images


def _extract_embedded_flate_images_from_pdf(pdf_bytes: bytes) -> list:
    import zlib
    images = []
    for m in re.finditer(rb'<<([^>]*?/Subtype\s*/Image[^>]*?)>>\s*stream\r?\n(.*?)\r?\nendstream', pdf_bytes, re.DOTALL):
        if len(images) >= 8:
            break
        header = m.group(1)
        if b'/FlateDecode' not in header or b'/DCTDecode' in header:
            continue
        w_m = re.search(rb'/Width\s+(\d+)', header)
        h_m = re.search(rb'/Height\s+(\d+)', header)
        bpc_m = re.search(rb'/BitsPerComponent\s+(\d+)', header)
        if not (w_m and h_m):
            continue
        w, h = int(w_m.group(1)), int(h_m.group(1))
        bpc = int(bpc_m.group(1)) if bpc_m else 8
        if w < 400 or h < 400 or bpc != 8:
            continue
        mode = 'RGB' if b'/DeviceRGB' in header else ('L' if b'/DeviceGray' in header else None)
        if not mode:
            continue
        try:
            raw = zlib.decompress(m.group(2))
            channels = 3 if mode == 'RGB' else 1
            expected = w * h * channels
            if len(raw) >= expected:
                im = Image.frombytes(mode, (w, h), raw[:expected])
                images.append(im)
        except Exception:
            continue
    return images



def _render_pdf_pages_python(tmpdir: str, src_pdf: str, out_prefix: str, dpi: int = 145, max_pages: int = 8):
    for old_p in Path(tmpdir).glob("page*.png"):
        old_p.unlink(missing_ok=True)
    errors = []
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(src_pdf)
        total = min(len(doc), max_pages)
        for idx in range(total):
            page = doc.load_page(idx)
            pix = page.get_pixmap(dpi=dpi)
            pix.save(f"{out_prefix}-{idx + 1:02d}.png")
        doc.close()
        pages = sorted(Path(tmpdir).glob("page*.png"))
        if pages:
            return pages, ""
    except Exception as exc:
        errors.append(f"fitz: {exc}")

    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(src_pdf)
        total = min(len(pdf), max_pages)
        scale = dpi / 72.0
        for idx in range(total):
            page = pdf[idx]
            bitmap = page.render(scale=scale)
            pil_img = bitmap.to_pil()
            pil_img.save(f"{out_prefix}-{idx + 1:02d}.png", format="PNG")
        pages = sorted(Path(tmpdir).glob("page*.png"))
        if pages:
            return pages, ""
    except Exception as exc:
        errors.append(f"pypdfium2: {exc}")

    return [], "; ".join(errors)


def _render_pdf_pages_resilient(tmpdir: str, pdf_path: str):
    import shutil
    out_prefix = f"{tmpdir}/page"
    has_pdftoppm = bool(shutil.which("pdftoppm"))
    first_err = ""

    # 1. Tentativa direta via pdftoppm (quando disponível no SO) ou fallback Python (PyMuPDF/pypdfium2)
    if has_pdftoppm:
        try:
            proc = subprocess.run(
                ["pdftoppm", "-png", "-r", "185", "-f", "1", "-l", "8", pdf_path, out_prefix],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            pages = sorted(Path(tmpdir).glob("page*.png"))
            if proc.returncode == 0 and pages:
                return pages, ""
            first_err = (proc.stderr or "").strip()
        except FileNotFoundError as exc:
            has_pdftoppm = False
            first_err = str(exc)

    pages, py_err = _render_pdf_pages_python(tmpdir, pdf_path, out_prefix)
    if pages:
        return pages, ""
    if not first_err and py_err:
        first_err = py_err

    # 2. Reparo em Python para "Invalid XRef entry 0" / tabela XRef fora do padrão
    try:
        raw_bytes = Path(pdf_path).read_bytes()
        rebuilt_bytes = _repair_pdf_xref_python(raw_bytes)
        if rebuilt_bytes:
            py_repaired = f"{tmpdir}/repaired_py.pdf"
            Path(py_repaired).write_bytes(rebuilt_bytes)
            if has_pdftoppm:
                for old_p in Path(tmpdir).glob("page*.png"):
                    old_p.unlink(missing_ok=True)
                proc_py = subprocess.run(
                    ["pdftoppm", "-png", "-r", "185", "-f", "1", "-l", "8", py_repaired, out_prefix],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                pages = sorted(Path(tmpdir).glob("page*.png"))
                if proc_py.returncode == 0 and pages:
                    return pages, ""
            pages, _ = _render_pdf_pages_python(tmpdir, py_repaired, out_prefix)
            if pages:
                return pages, ""
    except Exception:
        pass

    # 3. Reparo estrutural via qpdf ou Ghostscript
    repaired_pdf = f"{tmpdir}/repaired.pdf"
    repaired_ok = False
    if shutil.which("qpdf"):
        subprocess.run(
            ["qpdf", "--warning-exit-0", pdf_path, repaired_pdf],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        if Path(repaired_pdf).exists() and Path(repaired_pdf).stat().st_size > 0:
            repaired_ok = True
    elif shutil.which("gs"):
        subprocess.run(
            ["gs", "-o", repaired_pdf, "-sDEVICE=pdfwrite", pdf_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        if Path(repaired_pdf).exists() and Path(repaired_pdf).stat().st_size > 0:
            repaired_ok = True

    if repaired_ok:
        if has_pdftoppm:
            for old_p in Path(tmpdir).glob("page*.png"):
                old_p.unlink(missing_ok=True)
            proc2 = subprocess.run(
                ["pdftoppm", "-png", "-r", "185", "-f", "1", "-l", "8", repaired_pdf, out_prefix],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            pages = sorted(Path(tmpdir).glob("page*.png"))
            if proc2.returncode == 0 and pages:
                return pages, ""
        pages, _ = _render_pdf_pages_python(tmpdir, repaired_pdf, out_prefix)
        if pages:
            return pages, ""

    return [], first_err


def _iter_invoice_ocr(file_bytes: bytes, filename: str = "", mimetype: str = ""):
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key or api_key == 'SuaChaveAquiDoGoogle':
            yield {"error": "API Key do Gemini não configurada no .env"}
            return

        if not file_bytes or len(file_bytes) < 16:
            yield {"error": "O arquivo enviado está vazio (0 bytes). Aguarde o download concluir e tente novamente."}
            return

        head = file_bytes.lstrip()[:16]
        is_image_magic = (
            file_bytes[:3] == b'\xff\xd8\xff'
            or file_bytes[:8] == b'\x89PNG\r\n\x1a\n'
            or (file_bytes[:4] == b'RIFF' and file_bytes[8:12] == b'WEBP')
        )
        is_pdf_magic = b'%PDF-' in file_bytes[:2048]

        fname = (filename or '').lower()
        is_pdf = (not is_image_magic) and (is_pdf_magic or fname.endswith('.pdf') or mimetype == 'application/pdf')

        if is_pdf and not is_pdf_magic:
            yield {"error": "O arquivo selecionado não é um PDF válido (pode estar corrompido ou incompleto)."}
            return

        # Lista de tuplas: (page_num, total_pages, base64_data, mime_type)
        page_payloads = []
        if is_pdf:
            clean_pdf_bytes = _strip_pdf_header_noise(file_bytes)
            yield {"progress": 20, "stage": "Renderizando páginas do PDF..."}
            with tempfile.TemporaryDirectory() as tmpdir:
                pdf_path = f"{tmpdir}/nota.pdf"
                with open(pdf_path, "wb") as f_pdf:
                    f_pdf.write(clean_pdf_bytes)

                pages, pdf_err = _render_pdf_pages_resilient(tmpdir, pdf_path)
                if pages:
                    total_p = len(pages)
                    for idx, p_file in enumerate(pages, start=1):
                        with Image.open(p_file) as im:
                            page_payloads.append((idx, total_p, _prepare_page_b64(im, is_last_page=(idx == total_p)), "image/jpeg"))
                else:
                    # Fallback 1: extrai imagens JPEG embutidas no PDF (caso seja PDF escaneado)
                    embedded_imgs = _extract_embedded_jpegs_from_pdf(clean_pdf_bytes) or _extract_embedded_flate_images_from_pdf(clean_pdf_bytes)
                    if embedded_imgs:
                        total_p = len(embedded_imgs)
                        for idx, im in enumerate(embedded_imgs, start=1):
                            page_payloads.append((idx, total_p, _prepare_page_b64(im, is_last_page=(idx == total_p)), "image/jpeg"))
                    elif "password" in pdf_err.lower():
                        yield {"error": "Este PDF está protegido por senha. Remova a senha ou envie uma foto/print da nota."}
                        return
                    else:
                        # Fallback 2: leitura nativa de PDF diretamente pela IA (tolera XRef fora do padrão Poppler)
                        yield {"progress": 30, "stage": "PDF com XRef fora do padrão; ativando leitor nativo IA..."}
                        pdf_b64 = base64.b64encode(clean_pdf_bytes).decode('utf-8')
                        page_payloads.append((1, 1, pdf_b64, "application/pdf"))
        else:
            yield {"progress": 20, "stage": "Carregando imagem da nota..."}
            with Image.open(io.BytesIO(file_bytes)) as im:
                page_payloads.append((1, 1, _prepare_page_b64(im, is_last_page=True), "image/jpeg"))

        total_pages = len(page_payloads)
        merged_supplier = ""
        merged_invoice = ""
        all_raw_items = []

        if total_pages == 1:
            idx, tot, media_b64, m_type = page_payloads[0]
            stage_txt = (
                "IA lendo PDF nativo da NF..."
                if m_type == "application/pdf" else
                "IA lendo itens e unidades da NF..."
            )
            yield {"progress": 40, "stage": stage_txt}
            box = {"data": None, "error": None}

            def worker_single():
                try:
                    box["data"] = _call_gemini_fast(api_key, media_b64, page_num=1, total_pages=1, mime_type=m_type)
                except Exception as exc:
                    box["error"] = str(exc)

            t = threading.Thread(target=worker_single, daemon=True)
            t.start()
            pct = 40
            while t.is_alive():
                t.join(timeout=1.5)
                if t.is_alive() and pct < 88:
                    pct += 3
                    yield {"progress": pct, "stage": stage_txt}

            if box["error"]:
                yield {"error": f"Erro na IA: {box['error']}"}
                return
            page_results = [(1, box["data"] or {})]
        else:
            from concurrent.futures import ThreadPoolExecutor
            stage_txt = f"IA lendo {total_pages} páginas em paralelo..."
            yield {"progress": 40, "stage": stage_txt}

            def _run_page(payload_tuple):
                p_idx, p_tot, b64_data, mt = payload_tuple
                return p_idx, (_call_gemini_fast(api_key, b64_data, page_num=p_idx, total_pages=p_tot, mime_type=mt) or {})

            with ThreadPoolExecutor(max_workers=min(4, total_pages)) as pool:
                fut = pool.submit(lambda: list(pool.map(_run_page, page_payloads)))
                pct = 40
                while not fut.done():
                    time.sleep(1.5)
                    if not fut.done() and pct < 88:
                        pct += 3
                        yield {"progress": pct, "stage": stage_txt}
                try:
                    page_results = sorted(fut.result(), key=lambda x: x[0])
                except Exception as exc:
                    yield {"error": f"Erro na IA: {exc}"}
                    return

        for _, raw_p_data in page_results:
            p_data = _normalize_ocr_json_payload(raw_p_data)
            if not merged_supplier and p_data.get("supplier"):
                merged_supplier = str(p_data.get("supplier")).strip().upper()
            if not merged_invoice and p_data.get("invoice_number"):
                cand_nf = re.sub(r'\D', '', str(p_data.get("invoice_number") or ""))
                cand_nf = cand_nf.lstrip('0') or cand_nf
                if cand_nf:
                    merged_invoice = cand_nf
            if isinstance(p_data.get("items"), list):
                all_raw_items.extend(p_data["items"])

        yield {"progress": 94, "stage": f"Consolidando {len(all_raw_items)} itens..."}

        clean_items = []
        for it in all_raw_items:
            if not isinstance(it, dict):
                continue
            desc = str(it.get("description") or "").strip().upper()
            if not desc:
                continue
            raw_unit = str(it.get("unit") or "UN").strip().upper()
            if raw_unit in ("KGS", "QUILO", "QUILOS", "QUILOGRAMA", "QUILOGRAMAS"):
                raw_unit = "KG"

            raw_qty = max(0.001, float(it.get("quantity") or 1))
            pf = max(1, int(float(it.get("pack_factor") or 1)))

            m_apx_kg = re.search(r'\bAPX\.?\s*(\d+(?:[.,]\d+)?)\s*KG\b', desc)
            is_kg = (raw_unit == "KG") or (
                bool(m_apx_kg) and pf == 1 and abs(raw_qty - float(m_apx_kg.group(1).replace(',', '.'))) <= 1.5
            )

            if is_kg:
                weight_kg = round(raw_qty, 3)
                if m_apx_kg:
                    apx_box_kg = float(m_apx_kg.group(1).replace(',', '.'))
                    box_qty = max(1, int(round(weight_kg / apx_box_kg))) if apx_box_kg > 0 else 1
                else:
                    box_qty = 1
                clean_items.append({
                    "description": desc,
                    "unit": "KG",
                    "weight_kg": weight_kg,
                    "quantity": box_qty,
                    "pack_factor": 1,
                })
            else:
                qty = max(1, int(round(raw_qty)))
                if pf == 1:
                    m_pack = re.search(r'\b(\d{1,3})\s*[Xx]\s*\d+(?:[.,]\d+)?\s*(?:G|GR|KG|ML|L|UN|M)\b', desc)
                    if m_pack:
                        pf = max(1, int(m_pack.group(1)))
                clean_items.append({
                    "description": desc,
                    "unit": raw_unit or "UN",
                    "weight_kg": 0,
                    "quantity": qty,
                    "pack_factor": pf,
                })

        yield {
            "progress": 100,
            "done": True,
            "supplier": merged_supplier,
            "invoice_number": merged_invoice,
            "pages_processed": total_pages,
            "items": clean_items
        }

    except Exception as e:
        yield {"error": f"Erro na IA: {str(e)}"}



def _iter_invoice_ocr_multi(file_items: list):
    if len(file_items) == 1:
        f_bytes, f_name, f_mime = file_items[0]
        yield from _iter_invoice_ocr(f_bytes, f_name, f_mime)
        return

    total_pages = len(file_items)
    merged_supplier = ""
    merged_invoice = ""
    all_items = []

    for idx, (f_bytes, f_name, f_mime) in enumerate(file_items, start=1):
        base_pct = int(((idx - 1) / total_pages) * 88) + 4
        span_pct = max(5, int(88 / total_pages))
        yield {
            "progress": base_pct,
            "stage": f"Lendo foto {idx} de {total_pages} da NF..."
        }
        page_done = None
        for evt in _iter_invoice_ocr(f_bytes, f_name, f_mime):
            if "error" in evt:
                yield {"error": f"Erro na foto {idx}/{total_pages}: {evt['error']}"}
                return
            if evt.get("done"):
                page_done = evt
            elif isinstance(evt.get("progress"), (int, float)):
                scaled = min(96, base_pct + int((float(evt["progress"]) / 100.0) * span_pct))
                yield {
                    "progress": scaled,
                    "stage": f"Foto {idx}/{total_pages}: {evt.get('stage') or 'Extraindo itens...'}"
                }

        if page_done:
            if not merged_supplier and page_done.get("supplier"):
                merged_supplier = str(page_done["supplier"]).strip()
            if not merged_invoice and page_done.get("invoice_number"):
                merged_invoice = str(page_done["invoice_number"]).strip()
            if isinstance(page_done.get("items"), list):
                all_items.extend(page_done["items"])

    yield {
        "progress": 100,
        "done": True,
        "supplier": merged_supplier,
        "invoice_number": merged_invoice,
        "pages_processed": total_pages,
        "items": all_items,
    }


def _ocr_response_multi(file_items: list):
    wants_stream = 'application/x-ndjson' in request.headers.get('Accept', '')

    if wants_stream:
        def generate():
            for event in _iter_invoice_ocr_multi(file_items):
                yield json.dumps(event, ensure_ascii=False) + "\n"

        return Response(
            stream_with_context(generate()),
            mimetype='application/x-ndjson',
            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
        )

    final_data = {"items": []}
    for event in _iter_invoice_ocr_multi(file_items):
        if "error" in event:
            return jsonify({"error": event["error"]}), 500
        if event.get("done"):
            final_data = {
                "supplier": event.get("supplier", ""),
                "invoice_number": event.get("invoice_number", ""),
                "pages_processed": event.get("pages_processed", len(file_items)),
                "items": event.get("items", []),
            }
    return jsonify(final_data), 200


def _ocr_response(file_bytes: bytes, filename: str = "", mimetype: str = "", cleanup_path: Path = None):
    wants_stream = 'application/x-ndjson' in request.headers.get('Accept', '')

    if wants_stream:
        def generate():
            try:
                for event in _iter_invoice_ocr(file_bytes, filename, mimetype):
                    yield json.dumps(event, ensure_ascii=False) + "\n"
            finally:
                if cleanup_path:
                    cleanup_path.unlink(missing_ok=True)

        return Response(
            stream_with_context(generate()),
            mimetype='application/x-ndjson',
            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
        )

    final_data = {"items": []}
    try:
        for event in _iter_invoice_ocr(file_bytes, filename, mimetype):
            if "error" in event:
                return jsonify({"error": event["error"]}), 500
            if event.get("done"):
                final_data = {"items": event.get("items", [])}
        return jsonify(final_data), 200
    finally:
        if cleanup_path:
            cleanup_path.unlink(missing_ok=True)


def _get_kippe_db():
    base_dir = Path(__file__).resolve().parent
    db_path = base_dir / 'kippe.db'
    if not db_path.exists():
        db_path = Path('kippe.db')
    conn = connect_db(str(db_path))
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sku_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias_norm TEXT NOT NULL,
            supplier_norm TEXT NOT NULL DEFAULT '',
            raw_alias TEXT NOT NULL,
            sku TEXT NOT NULL,
            ean TEXT DEFAULT '',
            catalog_name TEXT DEFAULT '',
            pack_factor INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL,
            UNIQUE(alias_norm, supplier_norm)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sku_pack_defaults (
            sku TEXT PRIMARY KEY,
            pack_factor INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS receiving_pending_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier TEXT NOT NULL,
            invoice_number TEXT NOT NULL,
            submitted_by_id TEXT NOT NULL,
            submitted_by_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDENTE',
            items_json TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            resolved_at TEXT DEFAULT '',
            resolved_by TEXT DEFAULT ''
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS product_registration_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_description TEXT NOT NULL,
            suggested_ean TEXT DEFAULT '',
            supplier TEXT DEFAULT '',
            invoice_number TEXT DEFAULT '',
            nf_qty INTEGER NOT NULL DEFAULT 1,
            pack_factor INTEGER NOT NULL DEFAULT 1,
            batch_code TEXT DEFAULT '',
            expiration_date TEXT DEFAULT '',
            requested_by_id TEXT NOT NULL,
            requested_by_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDENTE',
            created_sku TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS institutional_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            category TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            actor_name TEXT NOT NULL,
            actor_role TEXT NOT NULL,
            target_ref TEXT DEFAULT '',
            summary TEXT NOT NULL,
            details_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS receiving_divergences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier TEXT NOT NULL,
            supplier_norm TEXT NOT NULL,
            invoice_number TEXT NOT NULL,
            sku TEXT NOT NULL,
            product_name TEXT DEFAULT '',
            expected_qty INTEGER NOT NULL,
            counted_qty INTEGER NOT NULL,
            divergence_qty INTEGER NOT NULL,
            reason TEXT NOT NULL,
            notes TEXT DEFAULT '',
            operator_id TEXT NOT NULL,
            operator_name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS conference_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_norm TEXT NOT NULL,
            invoice_number TEXT NOT NULL,
            sku TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            batch_code TEXT,
            expiration_date TEXT,
            operator_id TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    return conn


def _norm_catalog_text(s: str) -> str:
    s = unicodedata.normalize('NFD', str(s or ''))
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    s = re.sub(r'[^A-Z0-9\s]', ' ', s.upper()).strip()
    tokens = []
    for tok in s.split():
        # Normaliza plural simples em português (ex: SORTIDOS -> SORTID, BOMBONS -> BOMBON)
        if len(tok) >= 5 and tok.endswith('NS'):
            tok = tok[:-2] + 'M'
        elif len(tok) >= 5 and tok.endswith('S') and not tok.endswith('SS'):
            tok = tok[:-1]
        tokens.append(tok)
    return ' '.join(tokens)


def _extract_domain_product(obj) -> dict:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        sku = str(obj.get('id') or obj.get('sku') or '').strip()
        ean = str(obj.get('ean') or obj.get('barcode') or obj.get('gtin') or '').strip()
        name = str(obj.get('name') or obj.get('description') or sku).strip()
        brand = str(obj.get('brand') or '').strip()
        category = str(obj.get('category') or '').strip()
        supplier = str(obj.get('supplier') or obj.get('last_supplier') or '').strip()
    else:
        sku = str(getattr(obj, 'id', None) or getattr(obj, 'sku', None) or '').strip()
        ean = str(getattr(obj, 'ean', None) or getattr(obj, 'barcode', None) or getattr(obj, 'gtin', None) or '').strip()
        name = str(getattr(obj, 'name', None) or getattr(obj, 'description', None) or sku).strip()
        brand = str(getattr(obj, 'brand', None) or '').strip()
        category = str(getattr(obj, 'category', None) or '').strip()
        supplier = str(getattr(obj, 'supplier', None) or getattr(obj, 'last_supplier', None) or '').strip()
    if not sku:
        return {}
    return {
        'id': sku,
        'sku': sku,
        'ean': ean,
        'name': name,
        'brand': brand,
        'category': category,
        'last_supplier': supplier,
    }


def _query_native_products(raw_query: str) -> list:
    candidates = {}

    # 1. Busca exata por SKU ou EAN via product_query_use_case
    try:
        q_res = container.product_query_use_case.execute(identifier=raw_query.strip())
        if getattr(q_res, 'is_success', False) and getattr(q_res, 'value', None):
            d = _extract_domain_product(q_res.value)
            if d:
                candidates[d['sku']] = d
    except Exception:
        pass

    # 2. Busca por sugestão nativa (frase completa + tokens individuais para tolerar variações de NF)
    clean_words = [w for w in re.sub(r'[^A-Z0-9\s]', ' ', raw_query.upper()).split() if len(w) >= 3]
    queries_to_run = [raw_query.strip()]
    for w in sorted(clean_words, key=len, reverse=True)[:3]:
        if w not in queries_to_run:
            queries_to_run.append(w)

    for q_term in queries_to_run:
        if not q_term:
            continue
        try:
            res = container.product_suggestion_use_case.execute(query=q_term)
            items = res.value if hasattr(res, 'value') else res
            if isinstance(items, list):
                for item in items:
                    d = _extract_domain_product(item)
                    if d and d['sku'] not in candidates:
                        candidates[d['sku']] = d
        except Exception:
            pass

    return list(candidates.values())




def _get_active_operator_context():
    if (
        container.config.ENV == "testing"
        and "X-Test-Operator-Override" in request.headers
    ):
        ov_id = str(request.headers.get("X-Test-Operator-Override") or "").strip()
        ov_role = str(request.headers.get("X-Test-Operator-Role") or "").strip().upper()
        op_obj = container.operator_repository.get_by_id(ov_id) if ov_id else None
        if op_obj:
            return op_obj.id, op_obj.name, op_obj.role
        return ov_id or "TEST-OP", "Test Agent", ov_role or "ADMIN_SISTEMA"

    op_id = str(session.get("operator_id") or "").strip()
    op_name = str(session.get("operator_name") or op_id or "OPERADOR").strip()
    op_role = str(session.get("operator_role") or "").strip().upper()
    if op_id and not op_role:
        op_obj = container.operator_repository.get_by_id(op_id)
        if op_obj:
            op_role = op_obj.role
            op_name = op_obj.name
    return op_id, op_name, op_role or "OPERADOR"


@app.route('/api/receiving/requests/product', methods=['POST'])
def create_product_registration_request():
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    op_id, op_name, _ = _get_active_operator_context()
    data = request.json or {}
    raw_desc = str(data.get('raw_description') or data.get('description') or '').strip().upper()
    if not raw_desc:
        return jsonify({'error': 'Descrição do produto da NF é obrigatória.'}), 400

    suggested_ean = str(data.get('suggested_ean') or data.get('ean') or '').strip()
    supplier = str(data.get('supplier') or '').strip().upper()
    invoice_number = str(data.get('invoice_number') or '').strip()
    nf_qty = max(1, int(float(data.get('nf_qty') or 1)))
    pack_factor = max(1, int(float(data.get('pack_factor') or 1)))
    batch_code = str(data.get('batch_code') or '').strip().upper()
    expiration_date = str(data.get('expiration_date') or '').strip()
    now_iso = __import__('datetime').datetime.now().isoformat(timespec='seconds')

    conn = _get_kippe_db()
    try:
        existing = conn.execute(
            '''
            SELECT id FROM product_registration_requests
            WHERE status = 'PENDENTE'
              AND raw_description = ?
              AND supplier = ?
              AND invoice_number = ?
            LIMIT 1
            ''',
            (raw_desc, supplier, invoice_number),
        ).fetchone()
        if existing:
            return jsonify({
                'ok': True,
                'deduplicated': True,
                'request_id': int(existing['id']),
                'message': 'Solicitação já enviada anteriormente ao Estoquista.',
            }), 200

        cur = conn.execute(
            '''
            INSERT INTO product_registration_requests (
                raw_description, suggested_ean, supplier, invoice_number,
                nf_qty, pack_factor, batch_code, expiration_date,
                requested_by_id, requested_by_name, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDENTE', ?)
            ''',
            (
                raw_desc, suggested_ean, supplier, invoice_number,
                nf_qty, pack_factor, batch_code, expiration_date,
                op_id, op_name, now_iso,
            ),
        )
        conn.commit()
        req_id = int(cur.lastrowid)
    finally:
        conn.close()

    _record_audit_event(
        "PRODUCT_REQUESTED",
        "RECEBIMENTO",
        f"Solicitação de cadastro na doca: {raw_desc} (NF {invoice_number or 'S/N'})",
        target_ref=f"REQ-{req_id}",
    )
    return jsonify({
        'ok': True,
        'request_id': req_id,
        'message': 'Solicitação de cadastro enviada ao Estoquista.',
    }), 201


@app.route('/api/receiving/pending', methods=['GET'])
def list_receiving_pending():
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    _, _, op_role = _get_active_operator_context()
    if not AccessControl.can_approve_receiving(op_role):
        return jsonify({'error': 'Autorização negada: perfil sem acesso à fila de armazenagem.'}), 403

    conn = _get_kippe_db()
    try:
        conf_rows = conn.execute(
            "SELECT * FROM receiving_pending_queue WHERE status = 'PENDENTE' ORDER BY id DESC"
        ).fetchall()
        prod_rows = conn.execute(
            "SELECT * FROM product_registration_requests WHERE status = 'PENDENTE' ORDER BY id DESC"
        ).fetchall()
    finally:
        conn.close()

    conferences = []
    for r in conf_rows:
        try:
            parsed_items = json.loads(r['items_json'] or '[]')
        except Exception:
            parsed_items = []
        conferences.append({
            'id': int(r['id']),
            'supplier': r['supplier'],
            'invoice_number': r['invoice_number'],
            'submitted_by_id': r['submitted_by_id'],
            'submitted_by_name': r['submitted_by_name'],
            'status': r['status'],
            'items': parsed_items,
            'notes': r['notes'] or '',
            'created_at': r['created_at'],
        })

    product_requests = [
        {
            'id': int(r['id']),
            'raw_description': r['raw_description'],
            'suggested_ean': r['suggested_ean'] or '',
            'supplier': r['supplier'] or '',
            'invoice_number': r['invoice_number'] or '',
            'nf_qty': int(r['nf_qty'] or 1),
            'pack_factor': int(r['pack_factor'] or 1),
            'batch_code': r['batch_code'] or '',
            'expiration_date': r['expiration_date'] or '',
            'requested_by_id': r['requested_by_id'],
            'requested_by_name': r['requested_by_name'],
            'status': r['status'],
            'created_at': r['created_at'],
        }
        for r in prod_rows
    ]

    return jsonify({
        'pending_conferences_count': len(conferences),
        'pending_products_count': len(product_requests),
        'conferences': conferences,
        'product_requests': product_requests,
    }), 200


@app.route('/api/receiving/pending/<int:req_id>/resolve-product', methods=['POST'])
def resolve_pending_product_request(req_id: int):
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    _, _, op_role = _get_active_operator_context()
    if not AccessControl.can_manage_operational_catalog(op_role):
        return jsonify({'error': 'Autorização negada: apenas Estoquista ou Administrador pode resolver cadastros.'}), 403

    data = request.json or {}
    action = str(data.get('action') or 'CADASTRADO').strip().upper()
    created_sku = str(data.get('sku') or data.get('created_sku') or '').strip()
    ean = str(data.get('ean') or '').strip()
    catalog_name = str(data.get('name') or '').strip()
    now_iso = __import__('datetime').datetime.now().isoformat(timespec='seconds')

    conn = _get_kippe_db()
    try:
        row = conn.execute(
            "SELECT * FROM product_registration_requests WHERE id = ?",
            (req_id,),
        ).fetchone()
        if not row:
            return jsonify({'error': 'Solicitação não encontrada.'}), 404
        if row['status'] != 'PENDENTE':
            return jsonify({'error': f"Solicitação já encerrada ({row['status']})."}), 409

        new_status = 'DESCARTADO' if action == 'DESCARTADO' else 'CADASTRADO'
        conn.execute(
            "UPDATE product_registration_requests SET status = ?, created_sku = ? WHERE id = ?",
            (new_status, created_sku, req_id),
        )

        if new_status == 'CADASTRADO' and created_sku:
            alias_norm = _norm_catalog_text(row['raw_description'])
            sup_norm = _norm_catalog_text(row['supplier'] or '')
            pf = max(1, int(row['pack_factor'] or 1))
            conn.execute(
                '''
                INSERT INTO sku_aliases (alias_norm, supplier_norm, raw_alias, sku, ean, catalog_name, pack_factor, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(alias_norm, supplier_norm) DO UPDATE SET
                    sku = excluded.sku,
                    ean = excluded.ean,
                    catalog_name = excluded.catalog_name,
                    pack_factor = CASE WHEN excluded.pack_factor > 1 THEN excluded.pack_factor ELSE sku_aliases.pack_factor END,
                    updated_at = excluded.updated_at
                ''',
                (alias_norm, sup_norm, row['raw_description'], created_sku, ean, catalog_name or row['raw_description'], pf, now_iso),
            )
            if pf > 1:
                conn.execute(
                    '''
                    INSERT INTO sku_pack_defaults (sku, pack_factor, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(sku) DO UPDATE SET pack_factor = excluded.pack_factor, updated_at = excluded.updated_at
                    ''',
                    (created_sku, pf, now_iso),
                )
        conn.commit()
    finally:
        conn.close()

    return jsonify({'ok': True, 'status': new_status, 'sku': created_sku}), 200


@app.route('/api/receiving/pending/<int:queue_id>/approve', methods=['POST'])
def approve_pending_conference(queue_id: int):
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    op_id, _, op_role = _get_active_operator_context()
    if not AccessControl.can_approve_receiving(op_role):
        return jsonify({'error': 'Autorização negada: apenas Estoquista ou Administrador pode efetivar armazenagem.'}), 403

    data = request.json or {}
    sku_overrides = data.get('sku_overrides') or {}
    item_overrides = data.get('item_overrides') or {}
    now_iso = __import__('datetime').datetime.now().isoformat(timespec='seconds')

    conn = _get_kippe_db()
    try:
        row = conn.execute(
            "SELECT * FROM receiving_pending_queue WHERE id = ?",
            (queue_id,),
        ).fetchone()
        if not row:
            return jsonify({'error': 'Conferência pendente não encontrada.'}), 404
        if row['status'] != 'PENDENTE':
            return jsonify({'error': f"Esta conferência já foi processada ({row['status']})."}), 409

        items = json.loads(row['items_json'] or '[]')
        ctx_supplier = str(row['supplier'] or 'PADRAO').strip()
        ctx_invoice = str(row['invoice_number'] or '').strip()

        resolved_items = []
        for idx, it in enumerate(items):
            sku = str(sku_overrides.get(str(idx)) or it.get('sku') or '').strip()
            qty = int(it.get('quantity') or it.get('scanned') or 0)
            if qty <= 0:
                continue
            if not sku or sku.startswith('TEMP-'):
                return jsonify({
                    'error': f"O item '{it.get('name') or 'SEM SKU'}' ainda precisa ser cadastrado/vinculado antes de aprovar."
                }), 400
            prod = container.product_repository.get_by_id(sku)
            if not prod:
                return jsonify({'error': f"SKU '{sku}' não encontrado no catálogo."}), 400
            resolved_items.append((sku, qty, it))

        if not resolved_items:
            return jsonify({'error': 'Nenhum item válido com quantidade > 0 para aprovar.'}), 400

        committed = []
        for idx_pos, (sku, qty, it) in enumerate(resolved_items):
            ov = item_overrides.get(str(idx_pos)) or {}
            batch_code = str(ov.get('batch_code') if ov.get('batch_code') is not None else (it.get('batch_code') or '')).strip()
            expiration_date = str(ov.get('expiration_date') if ov.get('expiration_date') is not None else (it.get('expiration_date') or '')).strip()
            manufacturing_date = str(it.get('manufacturing_date') or '').strip()
            item_inv = str(it.get('invoice_number') or ctx_invoice or '').strip()
            res = container.receive_use_case.execute(
                identifier=sku,
                quantity=qty,
                batch_code=batch_code,
                expiration_date=expiration_date,
                supplier=ctx_supplier,
                manufacturing_date=manufacturing_date,
                origin_document=item_inv if item_inv else 'CONFERENCE',
                operator_id=op_id or 'SYSTEM',
            )
            if not res.is_success:
                return jsonify({'error': f"Falha ao dar entrada no SKU {sku}: {res.error}"}), 400

            committed.append({'sku': sku, 'quantity': qty, 'batch_code': batch_code, 'invoice_number': item_inv})
            conn.execute(
                "INSERT INTO conference_audit_log (supplier_norm, invoice_number, sku, quantity, batch_code, expiration_date, operator_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (_norm_catalog_text(ctx_supplier), item_inv, sku, qty, batch_code, expiration_date, op_id or 'SYSTEM', now_iso),
            )

        updated_items_snapshot = []
        for idx_pos, it in enumerate(items):
            ov = item_overrides.get(str(idx_pos)) or {}
            sku_final = str(sku_overrides.get(str(idx_pos)) or it.get('sku') or '').strip()
            batch_final = str(ov.get('batch_code') if ov.get('batch_code') is not None else (it.get('batch_code') or '')).strip()
            exp_final = str(ov.get('expiration_date') if ov.get('expiration_date') is not None else (it.get('expiration_date') or '')).strip()
            it_copy = dict(it)
            it_copy['sku'] = sku_final
            it_copy['batch_code'] = batch_final
            it_copy['expiration_date'] = exp_final
            updated_items_snapshot.append(it_copy)

        conn.execute(
            "UPDATE receiving_pending_queue SET status = 'APROVADO', items_json = ?, resolved_at = ?, resolved_by = ? WHERE id = ?",
            (json.dumps(updated_items_snapshot, ensure_ascii=False), now_iso, op_id or 'SYSTEM', queue_id),
        )
        conn.commit()
    finally:
        conn.close()

    _record_audit_event(
        "CONFERENCE_APPROVED",
        "ESTOQUE",
        f"Armazenagem aprovada: {ctx_supplier} · NF {ctx_invoice or 'S/N'} ({len(committed)} itens no estoque)",
        target_ref=f"NF-{ctx_invoice or queue_id}",
    )
    return jsonify({
        'ok': True,
        'approved': len(committed),
        'results': committed,
    }), 200


@app.route('/api/receiving/audit', methods=['GET'])
def search_receiving_audit():
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    query_text = str(request.args.get('q') or '').strip().upper()
    status_filter = str(request.args.get('status') or 'ALL').strip().upper()
    try:
        limit = min(200, max(1, int(request.args.get('limit') or 60)))
    except Exception:
        limit = 60

    conn = _get_kippe_db()
    try:
        op_rows = conn.execute("SELECT id, name, role FROM operators").fetchall()
        op_map = {str(r['id']): {'name': r['name'], 'role': r['role']} for r in op_rows}

        q_rows = conn.execute(
            "SELECT * FROM receiving_pending_queue ORDER BY id DESC LIMIT 300"
        ).fetchall()
        div_rows = conn.execute(
            "SELECT * FROM receiving_divergences ORDER BY id DESC LIMIT 500"
        ).fetchall()
        req_rows = conn.execute(
            "SELECT * FROM product_registration_requests ORDER BY id DESC LIMIT 500"
        ).fetchall()
        direct_log_rows = conn.execute(
            "SELECT * FROM conference_audit_log ORDER BY id DESC LIMIT 500"
        ).fetchall()
    finally:
        conn.close()

    div_by_key = {}
    for d in div_rows:
        key = (_norm_catalog_text(d['supplier'] or ''), str(d['invoice_number'] or '').strip())
        div_by_key.setdefault(key, []).append({
            'id': int(d['id']),
            'sku': d['sku'],
            'product_name': d['product_name'] or d['sku'],
            'expected_qty': int(d['expected_qty'] or 0),
            'counted_qty': int(d['counted_qty'] or 0),
            'divergence_qty': int(d['divergence_qty'] or 0),
            'reason': d['reason'] or '',
            'notes': d['notes'] or '',
            'operator_name': d['operator_name'] or d['operator_id'] or '',
            'created_at': d['created_at'] or '',
        })

    req_by_key = {}
    for pr in req_rows:
        key = (_norm_catalog_text(pr['supplier'] or ''), str(pr['invoice_number'] or '').strip())
        req_by_key.setdefault(key, []).append({
            'id': int(pr['id']),
            'raw_description': pr['raw_description'] or '',
            'suggested_ean': pr['suggested_ean'] or '',
            'nf_qty': int(pr['nf_qty'] or 1),
            'pack_factor': int(pr['pack_factor'] or 1),
            'status': pr['status'] or 'PENDENTE',
            'created_sku': pr['created_sku'] or '',
            'created_at': pr['created_at'] or '',
        })

    records = []
    seen_keys = set()

    for r in q_rows:
        sup = str(r['supplier'] or '').strip()
        inv = str(r['invoice_number'] or '').strip()
        st = str(r['status'] or 'PENDENTE').strip().upper()
        key = (_norm_catalog_text(sup), inv)
        if inv:
            seen_keys.add(key)

        try:
            raw_items = json.loads(r['items_json'] or '[]')
        except Exception:
            raw_items = []

        norm_items = []
        total_units = 0
        for it in raw_items:
            qty = int(it.get('quantity') or it.get('scanned') or 0)
            total_units += qty
            sku_val = str(it.get('sku') or '').strip()
            norm_items.append({
                'sku': sku_val,
                'name': str(it.get('name') or sku_val or 'ITEM SEM NOME').strip(),
                'quantity': qty,
                'batch_code': str(it.get('batch_code') or '').strip(),
                'expiration_date': str(it.get('expiration_date') or '').strip(),
                'is_unlinked': sku_val.startswith('TEMP-'),
            })

        res_by_id = str(r['resolved_by'] or '').strip()
        res_by_name = op_map.get(res_by_id, {}).get('name', res_by_id) if res_by_id else ''

        records.append({
            'protocol': f"REC-{int(r['id']):04d}",
            'queue_id': int(r['id']),
            'source': 'QUEUE',
            'supplier': sup or 'NÃO INFORMADO',
            'invoice_number': inv or 'S/N',
            'status': st,
            'submitted_by_id': r['submitted_by_id'] or '',
            'submitted_by_name': r['submitted_by_name'] or r['submitted_by_id'] or '',
            'created_at': r['created_at'] or '',
            'resolved_at': r['resolved_at'] or '',
            'resolved_by_id': res_by_id,
            'resolved_by_name': res_by_name,
            'notes': r['notes'] or '',
            'total_items': len(norm_items),
            'total_units': total_units,
            'items': norm_items,
            'divergences': div_by_key.get(key, []),
            'product_requests': req_by_key.get(key, []),
        })

    # Inclui também conferências efetivadas diretamente pelo Estoquista/Admin (fora da fila do conferente)
    direct_grouped = {}
    for lg in direct_log_rows:
        sup_norm = str(lg['supplier_norm'] or '').strip()
        inv = str(lg['invoice_number'] or '').strip()
        key = (sup_norm, inv)
        if inv and key in seen_keys:
            continue
        grp = direct_grouped.setdefault(key, {
            'protocol': f"DIR-{int(lg['id']):04d}",
            'queue_id': None,
            'source': 'DIRECT',
            'supplier': sup_norm or 'NÃO INFORMADO',
            'invoice_number': inv or 'S/N',
            'status': 'APROVADO',
            'submitted_by_id': lg['operator_id'] or '',
            'submitted_by_name': op_map.get(str(lg['operator_id'] or ''), {}).get('name', lg['operator_id'] or 'ESTOQUISTA'),
            'created_at': lg['created_at'] or '',
            'resolved_at': lg['created_at'] or '',
            'resolved_by_id': lg['operator_id'] or '',
            'resolved_by_name': op_map.get(str(lg['operator_id'] or ''), {}).get('name', lg['operator_id'] or 'ESTOQUISTA'),
            'notes': 'Conferência efetivada diretamente no estoque',
            'total_items': 0,
            'total_units': 0,
            'items': [],
            'divergences': div_by_key.get(key, []),
            'product_requests': req_by_key.get(key, []),
        })
        qty = int(lg['quantity'] or 0)
        sku_val = str(lg['sku'] or '').strip()
        prod_obj = container.product_repository.get_by_id(sku_val) if sku_val else None
        grp['items'].append({
            'sku': sku_val,
            'name': prod_obj.name if prod_obj else sku_val,
            'quantity': qty,
            'batch_code': str(lg['batch_code'] or '').strip(),
            'expiration_date': str(lg['expiration_date'] or '').strip(),
            'is_unlinked': False,
        })
        grp['total_items'] += 1
        grp['total_units'] += qty

    records.extend(direct_grouped.values())

    filtered = []
    for rec in records:
        if status_filter not in ('', 'ALL', 'TODOS') and rec['status'] != status_filter:
            continue
        if query_text:
            haystack_parts = [
                rec['protocol'],
                rec['supplier'],
                rec['invoice_number'],
                rec['submitted_by_name'],
                rec['submitted_by_id'],
                rec['resolved_by_name'],
                rec['status'],
            ]
            for it in rec['items']:
                haystack_parts.append(it['sku'])
                haystack_parts.append(it['name'])
                haystack_parts.append(it['batch_code'])
            haystack = " ".join(haystack_parts).upper()
            if query_text not in haystack:
                continue
        filtered.append(rec)

    summary = {
        'total': len(filtered),
        'pendente': sum(1 for r in filtered if r['status'] == 'PENDENTE'),
        'aprovado': sum(1 for r in filtered if r['status'] == 'APROVADO'),
        'rejeitado': sum(1 for r in filtered if r['status'] == 'REJEITADO'),
        'com_divergencia': sum(1 for r in filtered if len(r['divergences']) > 0),
    }

    return jsonify({
        'records': filtered[:limit],
        'summary': summary,
    }), 200


@app.route('/api/receiving/audit/reset', methods=['POST'])
def reset_receiving_audit_history():
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    op_id, op_name, op_role = _get_active_operator_context()
    if str(op_role or '').strip().upper() != 'ADMIN_SISTEMA':
        return jsonify({'error': 'Autorização negada: apenas o Administrador do Sistema pode zerar o histórico.'}), 403

    conn = _get_kippe_db()
    deleted_counts = {}
    try:
        for tbl in (
            'receiving_pending_queue',
            'product_registration_requests',
            'receiving_divergences',
            'conference_audit_log',
        ):
            cnt = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            deleted_counts[tbl] = int(cnt or 0)
            conn.execute(f"DELETE FROM {tbl}")
            conn.execute("DELETE FROM sqlite_sequence WHERE name = ?", (tbl,))

        conn.execute(
            "DELETE FROM institutional_audit_log WHERE category IN ('RECEBIMENTO', 'CONFERENCIA', 'ESTOQUE')"
        )
        conn.commit()
    finally:
        conn.close()

    _record_audit_event(
        "AUDIT_HISTORY_RESET",
        "GOVERNANCA",
        f"Histórico de recebimentos e auditoria zerado por {op_name or op_id} para início da operação",
        target_ref="RECEIVING-AUDIT",
    )
    return jsonify({'ok': True, 'deleted': deleted_counts}), 200


@app.route('/api/receiving/pending/<int:queue_id>/reject', methods=['POST'])
def reject_pending_conference(queue_id: int):
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    op_id, _, op_role = _get_active_operator_context()
    if not AccessControl.can_approve_receiving(op_role):
        return jsonify({'error': 'Autorização negada.'}), 403

    now_iso = __import__('datetime').datetime.now().isoformat(timespec='seconds')
    conn = _get_kippe_db()
    try:
        row = conn.execute("SELECT status FROM receiving_pending_queue WHERE id = ?", (queue_id,)).fetchone()
        if not row:
            return jsonify({'error': 'Conferência não encontrada.'}), 404
        if row['status'] != 'PENDENTE':
            return jsonify({'error': f"Conferência já encerrada ({row['status']})."}), 409
        conn.execute(
            "UPDATE receiving_pending_queue SET status = 'REJEITADO', resolved_at = ?, resolved_by = ? WHERE id = ?",
            (now_iso, op_id or 'SYSTEM', queue_id),
        )
        conn.commit()
    finally:
        conn.close()

    _record_audit_event(
        "CONFERENCE_REJECTED",
        "RECEBIMENTO",
        f"Conferência pendente #{queue_id} rejeitada",
        target_ref=f"FILA-{queue_id}",
    )
    return jsonify({'ok': True, 'status': 'REJEITADO'}), 200


@app.route('/api/catalog/aliases', methods=['POST'])
def save_catalog_alias():
    data = request.json or {}
    raw_alias = str(data.get('alias') or '').strip()
    sku = str(data.get('sku') or '').strip()
    if not raw_alias or not sku:
        return jsonify({'error': 'alias e sku obrigatórios'}), 400

    alias_norm = _norm_catalog_text(raw_alias)
    supplier_norm = _norm_catalog_text(str(data.get('supplier') or ''))
    ean = str(data.get('ean') or '').strip()
    catalog_name = str(data.get('name') or '').strip()
    pack_factor = max(1, int(data.get('pack_factor') or 1))
    now_iso = __import__('datetime').datetime.now().isoformat(timespec='seconds')

    explicit_factor = bool(data.get('explicit_factor', False))
    conn = _get_kippe_db()
    try:
        conn.execute('''
            INSERT INTO sku_aliases (alias_norm, supplier_norm, raw_alias, sku, ean, catalog_name, pack_factor, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(alias_norm, supplier_norm) DO UPDATE SET
                raw_alias = excluded.raw_alias,
                sku = excluded.sku,
                ean = excluded.ean,
                catalog_name = excluded.catalog_name,
                pack_factor = CASE
                    WHEN ? OR excluded.pack_factor > 1 THEN excluded.pack_factor
                    ELSE sku_aliases.pack_factor
                END,
                updated_at = excluded.updated_at
        ''', (alias_norm, supplier_norm, raw_alias, sku, ean, catalog_name, pack_factor, now_iso, 1 if explicit_factor else 0))

        if pack_factor > 1 or explicit_factor:
            conn.execute('''
                INSERT INTO sku_pack_defaults (sku, pack_factor, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(sku) DO UPDATE SET
                    pack_factor = excluded.pack_factor,
                    updated_at = excluded.updated_at
            ''', (sku, pack_factor, now_iso))
        conn.commit()
    finally:
        conn.close()

    return jsonify({'ok': True, 'sku': sku, 'pack_factor': pack_factor}), 200



@app.route('/api/catalog/batch-match', methods=['POST'])
def catalog_batch_match():
    data = request.json or {}
    items = data.get('items') or []
    supplier = (data.get('supplier') or '').strip()
    if not items or not isinstance(items, list):
        return jsonify({'matches': []})

    sup_norm = _norm_catalog_text(supplier)
    conn = _get_kippe_db()
    historical_skus = set()
    alias_rows = []
    sku_defaults = {}
    try:
        if sup_norm:
            for r in conn.execute(
                "SELECT DISTINCT sku FROM conference_audit_log WHERE supplier_norm = ?",
                (sup_norm,)
            ).fetchall():
                historical_skus.add(str(r['sku']))
            for r in conn.execute(
                "SELECT DISTINCT sku FROM sku_aliases WHERE supplier_norm = ?",
                (sup_norm,)
            ).fetchall():
                historical_skus.add(str(r['sku']))

        alias_rows = conn.execute(
            "SELECT alias_norm, supplier_norm, sku, ean, catalog_name, pack_factor FROM sku_aliases"
        ).fetchall()
        sku_defaults = {
            str(r['sku']): int(r['pack_factor'] or 1)
            for r in conn.execute("SELECT sku, pack_factor FROM sku_pack_defaults").fetchall()
        }
    finally:
        conn.close()

    # Carrega o catálogo uma única vez na memória para cruzar todos os itens da NF sem N+1 queries
    all_native_prods = []
    try:
        res_all = container.product_suggestion_use_case.execute(query="")
        raw_all = res_all.value if hasattr(res_all, 'value') else res_all
        for p in (raw_all or []):
            d = _extract_domain_product(p)
            if d:
                all_native_prods.append({
                    **d,
                    '_haystack': _norm_catalog_text(f"{d['sku']} {d.get('ean', '')} {d.get('name', '')} {d.get('brand', '')}"),
                    '_measures': set(re.findall(r'\b\d+(?:[.,]\d+)?\s*(?:G|GR|KG|ML|L|M)\b', (d.get('name', '')).upper().replace(',', '.'))),
                    '_sup_norm': _norm_catalog_text(d.get('last_supplier', '')),
                })
    except Exception:
        all_native_prods = []

    matches = []
    for raw_q in items:
        q = str(raw_q or '').strip()
        if not q:
            matches.append(None)
            continue

        q_norm = _norm_catalog_text(q)
        q_tokens = [t for t in q_norm.split() if len(t) >= 2] or [q_norm]
        q_measures = set(re.findall(r'\b\d+(?:[.,]\d+)?\s*(?:G|GR|KG|ML|L|M)\b', q.upper().replace(',', '.')))
        results_by_sku = {}

        for ar in alias_rows:
            a_norm = ar['alias_norm'] or ''
            if not a_norm:
                continue
            is_exact_alias = (a_norm == q_norm)
            matched_toks = sum(1 for t in q_tokens if t in a_norm)
            if is_exact_alias or matched_toks == len(q_tokens):
                sku = str(ar['sku'])
                sup_bonus = 0.25 if (sup_norm and ar['supplier_norm'] == sup_norm) else 0.0
                score = (2.0 if is_exact_alias else 1.2) + sup_bonus
                if sku not in results_by_sku or score > results_by_sku[sku]['score']:
                    results_by_sku[sku] = {
                        'id': sku,
                        'sku': sku,
                        'ean': str(ar['ean'] or ''),
                        'name': str(ar['catalog_name'] or sku),
                        'pack_factor': int(ar['pack_factor'] or 1),
                        'alias_match': is_exact_alias,
                        'score': round(score, 3),
                    }

        for prod in all_native_prods:
            sku = prod['sku']
            haystack = prod['_haystack']
            matched = sum(1 for t in q_tokens if t in haystack)
            if matched > 0 or q.upper() in sku.upper() or (prod.get('ean') and q in prod['ean']):
                base_score = matched / max(1, len(q_tokens))
                p_measures = prod['_measures']
                if q_measures and p_measures and not (q_measures & p_measures):
                    base_score -= 0.45
                sup_match = (sku in historical_skus) or (bool(sup_norm) and sup_norm in prod['_sup_norm'])
                score = base_score + (0.35 if sup_match else 0.0)
                if sku not in results_by_sku:
                    results_by_sku[sku] = {
                        'id': sku,
                        'sku': sku,
                        'ean': prod.get('ean', ''),
                        'name': prod.get('name', sku),
                        'pack_factor': 1,
                        'alias_match': False,
                        'score': round(score, 3),
                    }

        if not results_by_sku:
            matches.append(None)
            continue

        for item in results_by_sku.values():
            s_key = item['sku']
            if int(item.get('pack_factor') or 1) <= 1 and sku_defaults.get(s_key, 1) > 1:
                item['pack_factor'] = sku_defaults[s_key]

        best = sorted(results_by_sku.values(), key=lambda x: (-x['score'], x['name']))[0]
        matches.append(best)

    return jsonify({'matches': matches})


@app.route('/api/receiving/requests/product/batch', methods=['POST'])
def create_product_registration_requests_batch():
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    op_id, op_name, _ = _get_active_operator_context()
    data = request.json or {}
    req_items = data.get('items') or []
    if not req_items or not isinstance(req_items, list):
        return jsonify({'ok': True, 'created': 0}), 200

    now_iso = __import__('datetime').datetime.now().isoformat(timespec='seconds')
    conn = _get_kippe_db()
    created_count = 0
    try:
        for item in req_items:
            raw_desc = str(item.get('raw_description') or item.get('description') or '').strip().upper()
            if not raw_desc:
                continue
            suggested_ean = str(item.get('suggested_ean') or item.get('ean') or '').strip()
            supplier = str(item.get('supplier') or '').strip().upper()
            invoice_number = str(item.get('invoice_number') or '').strip()
            nf_qty = max(1, int(float(item.get('nf_qty') or 1)))
            pack_factor = max(1, int(float(item.get('pack_factor') or 1)))
            batch_code = str(item.get('batch_code') or '').strip().upper()
            expiration_date = str(item.get('expiration_date') or '').strip()

            existing = conn.execute(
                "SELECT id FROM product_registration_requests WHERE status = 'PENDENTE' AND raw_description = ? AND supplier = ? AND invoice_number = ? LIMIT 1",
                (raw_desc, supplier, invoice_number),
            ).fetchone()
            if existing:
                continue

            conn.execute(
                """
                INSERT INTO product_registration_requests (
                    raw_description, suggested_ean, supplier, invoice_number,
                    nf_qty, pack_factor, batch_code, expiration_date,
                    requested_by_id, requested_by_name, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDENTE', ?)
                """,
                (
                    raw_desc, suggested_ean, supplier, invoice_number,
                    nf_qty, pack_factor, batch_code, expiration_date,
                    op_id or 'SYSTEM', op_name or 'Conferente', now_iso,
                ),
            )
            created_count += 1
        conn.commit()
    finally:
        conn.close()

    return jsonify({'ok': True, 'created': created_count}), 201


@app.route('/api/catalog/search', methods=['GET'])
def catalog_search():
    q = (request.args.get('q') or '').strip()
    supplier = (request.args.get('supplier') or '').strip()
    if not q:
        return jsonify([])

    q_norm = _norm_catalog_text(q)
    sup_norm = _norm_catalog_text(supplier)
    q_tokens = [t for t in q_norm.split() if len(t) >= 2] or [q_norm]

    conn = _get_kippe_db()
    historical_skus = set()
    alias_rows = []
    try:
        if sup_norm:
            for r in conn.execute(
                "SELECT DISTINCT sku FROM conference_audit_log WHERE supplier_norm = ?",
                (sup_norm,)
            ).fetchall():
                historical_skus.add(str(r['sku']))
            for r in conn.execute(
                "SELECT DISTINCT sku FROM sku_aliases WHERE supplier_norm = ?",
                (sup_norm,)
            ).fetchall():
                historical_skus.add(str(r['sku']))

        alias_rows = conn.execute(
            "SELECT alias_norm, supplier_norm, sku, ean, catalog_name, pack_factor FROM sku_aliases"
        ).fetchall()
    finally:
        conn.close()

    results_by_sku = {}

    # 1. Verifica De-Para institucional salvo (sku_aliases)
    for ar in alias_rows:
        a_norm = ar['alias_norm'] or ''
        if not a_norm:
            continue
        is_exact_alias = (a_norm == q_norm)
        matched_toks = sum(1 for t in q_tokens if t in a_norm)
        if is_exact_alias or matched_toks == len(q_tokens):
            sku = str(ar['sku'])
            sup_bonus = 0.25 if (sup_norm and ar['supplier_norm'] == sup_norm) else 0.0
            score = (2.0 if is_exact_alias else 1.2) + sup_bonus
            if sku not in results_by_sku or score > results_by_sku[sku]['score']:
                results_by_sku[sku] = {
                    'id': sku,
                    'sku': sku,
                    'ean': str(ar['ean'] or ''),
                    'name': str(ar['catalog_name'] or sku),
                    'brand': '',
                    'category': '',
                    'pack_factor': int(ar['pack_factor'] or 1),
                    'alias_match': is_exact_alias,
                    'supplier_match': sku in historical_skus or (sup_norm and ar['supplier_norm'] == sup_norm),
                    'score': round(score, 3),
                }

    # 2. Consulta repositório oficial do KIPPE (use cases nativos)
    for prod in _query_native_products(q):
        sku = prod['sku']
        haystack = _norm_catalog_text(f"{sku} {prod.get('ean', '')} {prod.get('name', '')} {prod.get('brand', '')}")
        matched = sum(1 for t in q_tokens if t in haystack)
        if matched > 0 or q.upper() in sku.upper() or (prod.get('ean') and q in prod['ean']):
            base_score = matched / max(1, len(q_tokens))
            # Penaliza divergência de gramatura/volume (ex: 1.5KG vs 170G)
            q_measures = set(re.findall(r'\b\d+(?:[.,]\d+)?\s*(?:G|GR|KG|ML|L|M)\b', q.upper().replace(',', '.')))
            p_measures = set(re.findall(r'\b\d+(?:[.,]\d+)?\s*(?:G|GR|KG|ML|L|M)\b', (prod.get('name', '')).upper().replace(',', '.')))
            if q_measures and p_measures and not (q_measures & p_measures):
                base_score -= 0.45
            sup_match = (sku in historical_skus) or (
                bool(sup_norm) and sup_norm in _norm_catalog_text(prod.get('last_supplier', ''))
            )
            score = base_score + (0.35 if sup_match else 0.0)
            if sku not in results_by_sku:
                results_by_sku[sku] = {
                    **prod,
                    'pack_factor': 1,
                    'alias_match': False,
                    'supplier_match': sup_match,
                    'score': round(score, 3),
                }
            else:
                if prod.get('name'):
                    results_by_sku[sku]['name'] = prod['name']
                if prod.get('ean'):
                    results_by_sku[sku]['ean'] = prod['ean']
                if sup_match:
                    results_by_sku[sku]['supplier_match'] = True

    conn_pf = _get_kippe_db()
    try:
        sku_defaults = {
            str(r['sku']): int(r['pack_factor'] or 1)
            for r in conn_pf.execute("SELECT sku, pack_factor FROM sku_pack_defaults").fetchall()
        }
    finally:
        conn_pf.close()

    for item in results_by_sku.values():
        s_key = item['sku']
        if int(item.get('pack_factor') or 1) <= 1 and sku_defaults.get(s_key, 1) > 1:
            item['pack_factor'] = sku_defaults[s_key]

    ranked = sorted(results_by_sku.values(), key=lambda x: (-x['score'], x['name']))
    return jsonify(ranked[:15])


def _supabase_storage_config() -> tuple[str, str, str]:
    sb_url = os.getenv('SUPABASE_URL', '').strip().rstrip('/')
    sb_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '').strip()
    sb_bucket = os.getenv('SUPABASE_INVOICES_BUCKET', 'invoices-tmp').strip() or 'invoices-tmp'
    return sb_url, sb_key, sb_bucket


def _supabase_delete_objects(sb_url: str, sb_key: str, sb_bucket: str, paths: list[str]) -> None:
    if not (sb_url and sb_key and paths):
        return
    import urllib.request

    endpoint = f"{sb_url}/storage/v1/object/{sb_bucket}"
    body = json.dumps({'prefixes': paths}).encode('utf-8')
    req = urllib.request.Request(
        endpoint,
        data=body,
        method='DELETE',
        headers={
            'Authorization': f'Bearer {sb_key}',
            'apikey': sb_key,
            'Content-Type': 'application/json',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception:
        pass


@app.route('/api/invoices/upload-urls', methods=['POST'])
def invoices_signed_upload_urls():
    if not _has_valid_session():
        return jsonify({'error': 'Operador não autenticado.'}), 401

    sb_url, sb_key, sb_bucket = _supabase_storage_config()
    if not sb_url or not sb_key:
        return jsonify({'enabled': False}), 200

    data = request.json or {}
    files_meta = data.get('files') or []
    if not isinstance(files_meta, list) or not files_meta:
        return jsonify({'error': 'Nenhum metadado de arquivo informado.'}), 400
    if len(files_meta) > 12:
        return jsonify({'error': 'Limite máximo de 12 arquivos por nota fiscal.'}), 400

    import urllib.parse
    import urllib.request

    uploads = []
    for item in files_meta:
        raw_name = str((item or {}).get('name') or 'nota.pdf')
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', raw_name)[:80] or 'nota.pdf'
        mime_type = str((item or {}).get('type') or 'application/octet-stream')
        obj_path = f"ocr/{uuid.uuid4().hex}_{safe_name}"
        sign_endpoint = f"{sb_url}/storage/v1/object/upload/sign/{sb_bucket}/{urllib.parse.quote(obj_path)}"

        req = urllib.request.Request(
            sign_endpoint,
            data=b'{}',
            method='POST',
            headers={
                'Authorization': f'Bearer {sb_key}',
                'apikey': sb_key,
                'Content-Type': 'application/json',
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                payload = json.loads(resp.read().decode('utf-8'))
        except Exception as exc:
            return jsonify({'error': f'Falha ao preparar upload seguro no Supabase: {exc}'}), 502

        rel_url = str(payload.get('url') or '')
        if rel_url.startswith('http'):
            full_signed_url = rel_url
        elif rel_url.startswith('/storage/v1/'):
            full_signed_url = f"{sb_url}{rel_url}"
        elif rel_url.startswith('/'):
            full_signed_url = f"{sb_url}/storage/v1{rel_url}"
        else:
            full_signed_url = f"{sb_url}/storage/v1/{rel_url}"

        uploads.append({
            'path': obj_path,
            'signed_url': full_signed_url,
            'name': safe_name,
            'mime_type': mime_type,
        })

    return jsonify({'enabled': True, 'uploads': uploads}), 200


@app.route('/api/invoices/ocr', methods=['POST'])
def invoices_ocr():
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        storage_items = payload.get('storage_paths') or []
        if not isinstance(storage_items, list) or not storage_items:
            return jsonify({'error': 'Nenhum arquivo informado para OCR.'}), 400
        if len(storage_items) > 12:
            return jsonify({'error': 'Limite máximo de 12 fotos por nota fiscal.'}), 400

        sb_url, sb_key, sb_bucket = _supabase_storage_config()
        if not sb_url or not sb_key:
            return jsonify({'error': 'Supabase Storage não configurado no servidor.'}), 503

        import urllib.parse
        import urllib.request

        downloaded_items = []
        paths_to_cleanup = []
        try:
            for entry in storage_items:
                obj_path = str((entry or {}).get('path') or '').strip()
                if not re.fullmatch(r'ocr/[0-9a-f]{32}_[a-zA-Z0-9._-]+', obj_path):
                    return jsonify({'error': 'Caminho de arquivo temporário inválido.'}), 400

                paths_to_cleanup.append(obj_path)
                f_name = str((entry or {}).get('name') or obj_path.split('_', 1)[-1])
                f_mime = str((entry or {}).get('mime_type') or 'application/octet-stream')
                dl_url = f"{sb_url}/storage/v1/object/{sb_bucket}/{urllib.parse.quote(obj_path)}"
                req = urllib.request.Request(
                    dl_url,
                    method='GET',
                    headers={
                        'Authorization': f'Bearer {sb_key}',
                        'apikey': sb_key,
                    },
                )
                with urllib.request.urlopen(req, timeout=25) as resp:
                    f_bytes = resp.read()
                downloaded_items.append((f_bytes, f_name, f_mime))

            if len(downloaded_items) == 1:
                f_bytes, f_name, f_mime = downloaded_items[0]
                return _ocr_response(f_bytes, f_name, f_mime)

            return _ocr_response_multi(downloaded_items)
        finally:
            _supabase_delete_objects(sb_url, sb_key, sb_bucket, paths_to_cleanup)

    raw_files = request.files.getlist('files') or request.files.getlist('file')
    valid_files = [f for f in raw_files if f and getattr(f, 'filename', '')]
    if not valid_files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    if len(valid_files) > 12:
        return jsonify({'error': 'Limite máximo de 12 fotos por nota fiscal.'}), 400

    file_items = [
        (f.read(), f.filename, f.mimetype or 'image/jpeg')
        for f in valid_files
    ]
    if len(file_items) == 1:
        f_bytes, f_name, f_mime = file_items[0]
        return _ocr_response(f_bytes, f_name, f_mime)

    return _ocr_response_multi(file_items)


@app.route('/share-target', methods=['POST'])
def share_target():
    file = request.files.get('file')
    if not file or not file.filename:
        return redirect('/?share_error=empty', code=303)

    token = uuid.uuid4().hex
    ext = Path(file.filename).suffix.lower() or '.pdf'
    target_path = SHARE_TMP_DIR / f"{token}{ext}"
    file.save(target_path)
    return redirect(f'/?share_id={token}', code=303)


@app.route('/api/invoices/shared/<token>', methods=['GET'])
def invoices_shared(token):
    if not re.fullmatch(r'[0-9a-f]{32}', token):
        return jsonify({'error': 'Token inválido'}), 400

    matches = list(SHARE_TMP_DIR.glob(f"{token}.*"))
    if not matches:
        return jsonify({'error': 'Arquivo compartilhado expirado ou já processado'}), 404

    file_path = matches[0]
    return _ocr_response(file_path.read_bytes(), file_path.name, cleanup_path=file_path)

if __name__ == '__main__':
    is_dev = (
        container.config.ENV
        == 'development'
    )

    app.run(
        host=container.config.HOST,
        port=container.config.PORT,
        debug=is_dev
    )
