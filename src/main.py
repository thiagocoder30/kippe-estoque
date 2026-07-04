import json
import re
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Importações estáveis do Domínio e Apresentação
from src.presentation.api.warehouse_router import WarehouseAPIRouter
from src.application.warehouse.query_service import InventoryQueryService
from src.application.warehouse.command_bus import CommandBus
from src.application.warehouse.commands import (
    ReceiveGoodsCommand, TransferToStoreCommand, RegisterAdjustmentCommand
)
from src.application.warehouse.use_cases.receive_goods import ReceiveGoodsHandler
from src.application.warehouse.use_cases.transfer_to_store import TransferToStoreHandler
from src.application.warehouse.use_cases.register_adjustment import RegisterAdjustmentHandler
from src.domain.warehouse.ledger_repository import InventoryAccountRepository
from src.domain.warehouse.ledger import InventoryAccount

# =========================================================
# INFRAESTRUTURA EM MEMÓRIA (Catálogo Dinâmico Inteligente)
# =========================================================
class FakeCatalog:
    def __init__(self):
        self.products = {
            "789609890001": {"description": "Detergente Ypê 500 ml", "brand": "Ypê", "category": "LIMPEZA"}
        }

    def register_product(self, sku, description, category):
        self.products[sku] = {
            "description": description.strip() if description else "Produto Não Identificado",
            "brand": "Genérica",
            "category": category.strip() if category else "GERAL"
        }

    def get_by_sku(self, sku):
        data = self.products.get(sku, {"description": "Produto Sem Cadastro", "brand": "N/A", "category": "GERAL"})
        class Product: pass
        p = Product()
        p.description = data["description"]
        p.brand = data["brand"]
        p.category = data["category"]
        return p

class InMemoryLedgerRepo(InventoryAccountRepository):
    def __init__(self):
        self.accounts = {}
    def save(self, account: InventoryAccount) -> None:
        self.accounts[account.sku] = account
    def get_by_sku(self, sku: str) -> InventoryAccount:
        return self.accounts.get(sku)
    def get_all(self):
        return list(self.accounts.values())

# Inicialização do estado centralizado
repo = InMemoryLedgerRepo()
catalog = FakeCatalog()
query_svc = InventoryQueryService(ledger_repo=repo, catalog_repo=catalog)
bus = CommandBus()

bus.register(ReceiveGoodsCommand, ReceiveGoodsHandler(repo, catalog))
bus.register(TransferToStoreCommand, TransferToStoreHandler(repo, catalog))
bus.register(RegisterAdjustmentCommand, RegisterAdjustmentHandler(repo, catalog))

warehouse_api = WarehouseAPIRouter(query_service=query_svc, command_bus=bus)

print("\n[INFO] Injetando lote inicial de Detergente Ypê no Ledger em memória...")
warehouse_api.post_receive_goods({
    "sku": "789609890001", "quantity": 20, "supplier": "Indústria Ypê",
    "batch_code": "LOTE-AGORA", "expiration_date": "2027-01-01",
    "invoice_id": "NF-1001", "operator": "Thiago"
})
warehouse_api.post_transfer_to_store({
    "sku": "789609890001", "quantity": 5, "batch_code": "LOTE-AGORA", "operator": "Repositor"
})
warehouse_api.post_register_adjustment({
    "sku": "789609890001", "quantity": -2, "batch_code": "LOTE-AGORA",
    "divergence_type": "UNREGISTERED_WITHDRAWAL",
    "reason": "Perda na prateleira", "operator": "Auditoria"
})

# =========================================================
# GATEWAY HTTP NATIVO
# =========================================================
class KippeHTTPGateway(BaseHTTPRequestHandler):
    
    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type')

    def _write_json_response(self, status_code: int, body: dict):
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

        sku_match = re.match(r'^/api/sku/([^/]+)$', self.path)
        if sku_match:
            sku = sku_match.group(1)
            status_code, body = warehouse_api.get_sku(sku)
            self._write_json_response(status_code, body)
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
            # Atualiza o catálogo dinâmico em memória com os dados vitais inseridos
            sku = payload.get("sku")
            description = payload.get("description")
            category = payload.get("category")
            if sku and description:
                catalog.register_product(sku, description, category)

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

