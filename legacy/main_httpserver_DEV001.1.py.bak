import json
import re
import os
from urllib.parse import unquote
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from src.presentation.api.warehouse_router import WarehouseAPIRouter
from src.application.warehouse.query_service import InventoryQueryService
from src.application.warehouse.command_bus import CommandBus
from src.application.warehouse.commands import (
    ReceiveGoodsCommand, TransferToStoreCommand, RegisterAdjustmentCommand
)
from src.application.warehouse.use_cases.receive_goods import ReceiveGoodsHandler
from src.application.warehouse.use_cases.transfer_to_store import TransferToStoreHandler
from src.application.warehouse.use_cases.register_adjustment import RegisterAdjustmentHandler

from src.infrastructure.database import SQLiteLedgerRepo, SQLiteCatalog

repo = SQLiteLedgerRepo(db_path="kippe.db")
catalog = SQLiteCatalog(db_path="kippe.db")

query_svc = InventoryQueryService(ledger_repo=repo, catalog_repo=catalog)
bus = CommandBus()

bus.register(ReceiveGoodsCommand, ReceiveGoodsHandler(repo, catalog))
bus.register(TransferToStoreCommand, TransferToStoreHandler(repo, catalog))
bus.register(RegisterAdjustmentCommand, RegisterAdjustmentHandler(repo, catalog))

warehouse_api = WarehouseAPIRouter(query_service=query_svc, command_bus=bus)

class KippeHTTPGateway(BaseHTTPRequestHandler):
    
    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type')

    def _write_json_response(self, status_code: int, body: list | dict):
        self.send_response(status_code)
        self._set_cors_headers()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        response_bytes = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith('/web/'):
            try:
                filepath = self.path.split('?')[0].lstrip('/')
                if '..' in filepath:
                    self._write_json_response(403, {"error": "Acesso negado."})
                    return
                with open(filepath, 'rb') as f:
                    content = f.read()
                
                self.send_response(200)
                if filepath.endswith('.html'):
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                elif filepath.endswith('.css'):
                    self.send_header('Content-Type', 'text/css')
                elif filepath.endswith('.js'):
                    self.send_header('Content-Type', 'application/javascript; charset=utf-8')
                elif filepath.endswith('.json'):
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                elif filepath.endswith('.png'):
                    self.send_header('Content-Type', 'image/png')
                self.end_headers()
                self.wfile.write(content)
                return
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Arquivo nao encontrado.")
                return
            except Exception:
                self.send_response(500)
                self.end_headers()
                return

        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/web/index.html')
            self.end_headers()
            return

        if self.path == '/health':
            self._write_json_response(200, {"status": "ok", "system": "KIPPE PLATFORM v1.0 (Native HTTP)"})
            return

        if self.path.startswith('/api/search'):
            query_params = self.path.split('?')
            if len(query_params) > 1:
                params = dict(qc.split('=') for qc in query_params[1].split('&') if '=' in qc)
                term = unquote(params.get('q', ''))
                if term:
                    results = catalog.search_by_term(term)
                    self._write_json_response(200, results)
                    return
            self._write_json_response(200, [])
            return


        # --- MÓDULO ENTERPRISE: RELATÓRIO FEFO ---
        if self.path.split('?')[0] == '/api/relatorios/vencimentos':
            import sqlite3
            from datetime import datetime
            try:
                conn = sqlite3.connect('kippe.db')
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                query = '''
                    SELECT b.sku, b.batch_code, b.expiration, b.quantity, b.quantity_store, b.store_balance, c.description
                    FROM batches b
                    LEFT JOIN catalog c ON b.sku = c.sku
                    WHERE b.expiration IS NOT NULL AND b.expiration != ''
                '''
                rows = cur.execute(query).fetchall()
                conn.close()

                result = []
                today = datetime.now()
                for r in rows:
                    try:
                        exp_str = str(r['expiration']).split(' ')[0]
                        exp_date = None
                        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S'):
                            try:
                                exp_date = datetime.strptime(exp_str, fmt)
                                break
                            except: pass
                        if not exp_date: continue
                        dias = (exp_date - today).days

                        if dias > 60: continue

                        if dias < 0: status = "⚫ VENCIDO"
                        elif dias <= 15: status = "🔴 CRÍTICO"
                        elif dias <= 30: status = "🟠 ALERTA"
                        else: status = "🟡 ATENÇÃO"

                        desc = r['description'] if r['description'] else 'PRODUTO SEM NOME'
                        q_wh = int(r['quantity'] or 0)
                        q_st = int(r['quantity_store'] or 0)
                        q_bal = int(r['store_balance'] or 0)
                        total_stock = q_wh + q_st + q_bal

                        result.append({
                            "sku": str(r['sku']),
                            "name": f"{status} | {desc}",
                            "expiration": f"{exp_str} ({dias} DIAS) | ESTOQUE TOTAL: {total_stock} UN",
                            "batch": str(r['batch_code']),
                            "sort_days": dias
                        })
                    except Exception:
                        pass
                result.sort(key=lambda x: x['sort_days'])
                for item in result: 
                    if 'sort_days' in item: del item['sort_days']
                
                self._write_json_response(200, result)
                return
            except Exception as e:
                import traceback
                print(f"ERRO FEFO: {traceback.format_exc()}")
                self._write_json_response(200, [{"sku": "ERR", "name": "ERRO BANCO DE DADOS", "expiration": str(e), "batch": "CRASH"}])
                return

        # --- BUSCA INTELIGENTE (SKU OU CÓDIGO DE BARRAS) ---
        # Suporta tanto /api/sku/ quanto /api/produto/ para bater com o Frontend
        sku_match = re.match(r'^/api/(?:sku|produto)/([^/]+)$', self.path)
        if sku_match:
            from urllib.parse import unquote
            sku_or_barcode = unquote(sku_match.group(1))
            true_sku = sku_or_barcode

            # Tenta descobrir o verdadeiro SKU se a busca for por Código de Barras
            try:
                import sqlite3
                conn = sqlite3.connect('kippe.db')
                conn.row_factory = sqlite3.Row
                c_row = conn.cursor().execute("SELECT sku FROM catalog WHERE sku = ? OR barcode = ?", (sku_or_barcode, sku_or_barcode)).fetchone()
                if c_row:
                    true_sku = c_row['sku']
                conn.close()
            except Exception:
                pass

            # Busca no Motor Institucional (CQRS)
            status_code, response_data = warehouse_api.get_sku(true_sku)

            if status_code == 200:
                try:
                    product_meta = catalog.get_by_sku(true_sku)
                    response_data["photo"] = getattr(product_meta, "photo", None)
                except:
                    pass

            self._write_json_response(status_code, response_data)
            return


        self._write_json_response(404, {"error": "Rota não encontrada."})

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            payload = json.loads(post_data.decode('utf-8'))
        except Exception:
            self._write_json_response(400, {"error": "Payload inválido. Falha ao parsear JSON."})
            return

        if self.path == '/api/receive':
            sku = payload.get("sku")
            description = payload.get("description")
            category = payload.get("category")
            photo = payload.get("photo") # Captura a string comprimida em base64 da imagem
            if sku and description:
                catalog.register_product(sku, description, category, photo)

            status_code, body = warehouse_api.post_receive_goods(payload)
            self._write_json_response(status_code, body)
            return
            
        elif self.path == '/api/transfer':
            status_code, body = warehouse_api.post_transfer_to_store(payload)
            self._write_json_response(status_code, body)
            return
            
        elif self.path == '/api/adjustment':
            status_code, body = warehouse_api.post_register_adjustment(payload)
            self._write_json_response(status_code, body)
            return

        self._write_json_response(404, {"error": "Rota de comando não encontrada."})

def run(port=8000):
    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, KippeHTTPGateway)
    print(f"\n\033[92m[OK] KIPPE NATIVE HTTP GATEWAY OPERANDO EM PORTA {port}...\033[0m")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\033[93m[INFO] Encerrando o servidor HTTP institucional...\033[0m")
        httpd.server_close()

if __name__ == '__main__':
    run()

