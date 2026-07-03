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
# INFRAESTRUTURA EM MEMÓRIA (Mocks idênticos aos testes E2E)
# =========================================================
class FakeCatalog:
    def get_by_sku(self, sku):
        class Product:
            description = "Detergente Ypê 500 ml" if sku == "789609890001" else "Produto Teste"
            brand = "Ypê"
            category = "LIMPEZA"
        return Product()

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

# Registro de Handlers no Barramento de Comandos
bus.register(ReceiveGoodsCommand, ReceiveGoodsHandler(repo, catalog))
bus.register(TransferToStoreCommand, TransferToStoreHandler(repo, catalog))
bus.register(RegisterAdjustmentCommand, RegisterAdjustmentHandler(repo, catalog))

# Instância única do Roteador de Fronteira
warehouse_api = WarehouseAPIRouter(query_service=query_svc, command_bus=bus)

# =========================================================
# GATEWAY HTTP NATIVO (Sem dependências externas)
# =========================================================
class KippeHTTPGateway(BaseHTTPRequestHandler):
    
    def _set_cors_headers(self):
        """Injeta os cabeçalhos necessários para comunicação com o PWA/Frontend local"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type')

    def _write_json_response(self, status_code: int, body: dict):
        """Serializa e envia a resposta padronizada em formato JSON"""
        self.send_response(status_code)
        self._set_cors_headers()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        
        response_bytes = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        """Trata as requisições de preflight enviadas por navegadores modernos"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        # 1. Servidor de Arquivos Estáticos (PWA Frontend)
        if self.path.startswith('/web/'):
            try:
                # Resolve o caminho do arquivo removendo parâmetros de query
                filepath = self.path.split('?')[0].lstrip('/')
                
                # Proteção básica contra path traversal
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
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                return

        # 2. Rota raiz redireciona diretamente para o Dashboard PWA
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/web/index.html')
            self.end_headers()
            return

        # 3. Endpoint de Verificação de Saúde
        if self.path == '/health':
            self._write_json_response(200, {"status": "ok", "system": "KIPPE PLATFORM v1.0 (Native HTTP)"})
            return

        # 4. Roteamento dinâmico por Regex para extração do SKU: /api/sku/{sku}
        sku_match = re.match(r'^/api/sku/([^/]+)$', self.path)
        if sku_match:
            sku = sku_match.group(1)
            status_code, body = warehouse_api.get_sku(sku)
            self._write_json_response(status_code, body)
            return

        self._write_json_response(404, {"error": "Rota de consulta não encontrada."})

    def do_POST(self):
        # Captura e decodificação do corpo da requisição JSON
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            payload = json.loads(post_data.decode('utf-8'))
        except Exception:
            self._write_json_response(400, {"error": "Payload inválido. Falha ao parsear JSON."})
            return

        # Roteamento dos comandos operacionais do write-side
        if self.path == '/api/receive':
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

# =========================================================
# INICIALIZAÇÃO DO SERVIDOR
# =========================================================
def run(port=8000):
    server_address = ('', port)
    # ThreadingHTTPServer evita travamento de conexões abertas no celular
    httpd = ThreadingHTTPServer(server_address, KippeHTTPGateway)
    print(f"\n\033[92m[OK] KIPPE NATIVE HTTP GATEWAY OPERANDO EM PORTA {port}...\033[0m")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\033[93m[INFO] Encerrando o servidor HTTP institucional...\033[0m")
        httpd.server_close()

if __name__ == '__main__':
    run()

