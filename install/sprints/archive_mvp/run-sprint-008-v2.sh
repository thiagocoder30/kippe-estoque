#!/bin/bash
# Kippe-Estoque Core | Sprint 008 (V2): FEFO Otimizado com Lotes e Pick-List de Gôndola

SPRINT_ID="008-v2"
LOG_DIR="/sdcard/Download/kippe-estoque/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/sprint-${SPRINT_ID}-${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

{
    echo "=== Iniciando Sprint $SPRINT_ID - Kippe-Estoque Core (FEFO Institucional) ==="
    echo "Data/Hora: $(date)"

    # 1. Domínio Core Refatorado (O(N log N) determinístico para lotes)
    cat << 'EOF' > src/domain/product.py
from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime
from .result import Result

@dataclass
class Product:
    id: str
    name: str
    quantity: int
    # Estrutura: { 'LOTE123': {'exp': 'YYYY-MM-DD', 'qty': int} }
    batches: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def add_stock(self, amount: int, expiration_date: str, batch_code: str) -> Result[None, str]:
        if amount <= 0:
            return Result.fail("Quantidade deve ser maior que zero.")
        if not batch_code:
            return Result.fail("O código do Lote é obrigatório.")
            
        try:
            exp_date = datetime.strptime(expiration_date, "%Y-%m-%d").date()
            if exp_date <= datetime.today().date():
                return Result.fail("BLOQUEIO DE DOCA: Mercadoria vencida ou vence hoje.")
        except ValueError:
            return Result.fail("Formato de data inválido (Use YYYY-MM-DD).")

        self.quantity += amount
        current_qty = self.batches.get(batch_code, {}).get('qty', 0)
        self.batches[batch_code] = {'exp': expiration_date, 'qty': current_qty + amount}
        return Result.ok(None)

    def remove_stock(self, amount: int) -> Result[None, str]:
        if amount <= 0: return Result.fail("Quantidade inválida.")
        if self.quantity < amount: return Result.fail("Estoque físico insuficiente.")

        remaining = amount
        # Ordena cronologicamente pela data, desempata pelo código do lote
        sorted_batches = sorted(self.batches.items(), key=lambda x: (x[1]['exp'], x[0]))

        for batch_code, data in sorted_batches:
            if remaining == 0: break
            batch_qty = data['qty']
            
            if batch_qty <= 0: continue

            if batch_qty >= remaining:
                self.batches[batch_code]['qty'] -= remaining
                remaining = 0
            else:
                remaining -= batch_qty
                self.batches[batch_code]['qty'] = 0

        # Limpeza atômica dos lotes vazios
        self.batches = {k: v for k, v in self.batches.items() if v['qty'] > 0}
        self.quantity -= amount
        return Result.ok(None)
        
    def get_picking_instructions(self) -> list:
        """Gera a lista de separação (Pick-List) para a gôndola ordenada por FEFO."""
        sorted_batches = sorted(self.batches.items(), key=lambda x: (x[1]['exp'], x[0]))
        return [{"lote": k, "validade": v['exp'], "qtd_disponivel": v['qty']} for k, v in sorted_batches]
EOF

    # 2. Persistência (Migrations ACID para Tabela de Lotes Complexa)
    cat << 'EOF' > src/interfaces/sqlite_repository.py
import sqlite3
from typing import List, Optional, Dict, Any
from src.domain.product import Product

class SQLiteProductRepository:
    def __init__(self, db_path: str = "estoque_producao.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    quantity INTEGER NOT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS batches (
                    product_id TEXT NOT NULL,
                    batch_code TEXT NOT NULL,
                    expiration_date TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    PRIMARY KEY (product_id, batch_code)
                )
            ''')
            conn.commit()

    def save(self, product: Product) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO products (id, name, quantity) 
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET 
                    name=excluded.name, quantity=excluded.quantity
            ''', (product.id, product.name, product.quantity))
            
            conn.execute('DELETE FROM batches WHERE product_id = ?', (product.id,))
            for batch_code, data in product.batches.items():
                conn.execute('''
                    INSERT INTO batches (product_id, batch_code, expiration_date, quantity) 
                    VALUES (?, ?, ?, ?)
                ''', (product.id, batch_code, data['exp'], data['qty']))
            conn.commit()

    def log_transaction(self, product_id: str, trans_type: str, amount: int) -> None:
        with self._get_connection() as conn:
            conn.execute('INSERT INTO transactions (product_id, type, amount) VALUES (?, ?, ?)', (product_id, trans_type, amount))
            conn.commit()

    def get_by_id(self, product_id: str) -> Optional[Product]:
        with self._get_connection() as conn:
            prod_row = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
            if not prod_row: return None
            
            batch_rows = conn.execute('SELECT batch_code, expiration_date, quantity FROM batches WHERE product_id = ?', (product_id,)).fetchall()
            batches_dict = {row['batch_code']: {'exp': row['expiration_date'], 'qty': row['quantity']} for row in batch_rows}
            
            return Product(id=prod_row['id'], name=prod_row['name'], quantity=prod_row['quantity'], batches=batches_dict)

    def get_all(self) -> List[Product]:
        with self._get_connection() as conn:
            rows = conn.execute('SELECT * FROM products ORDER BY name').fetchall()
            products = []
            for row in rows:
                batch_rows = conn.execute('SELECT batch_code, expiration_date, quantity FROM batches WHERE product_id = ? ORDER BY expiration_date', (row['id'],)).fetchall()
                batches_dict = {b['batch_code']: {'exp': b['expiration_date'], 'qty': b['quantity']} for b in batch_rows}
                products.append(Product(id=row['id'], name=row['name'], quantity=row['quantity'], batches=batches_dict))
            return products

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute('''
                SELECT t.id, t.type, t.amount, datetime(t.timestamp, 'localtime') as data, p.name 
                FROM transactions t
                JOIN products p ON t.product_id = p.id
                ORDER BY t.id DESC LIMIT ?
            ''', (limit,)).fetchall()
            return [dict(row) for row in rows]
EOF

    # 3. Orquestrador de Casos de Uso
    cat << 'EOF' > src/use_cases/manage_stock.py
from typing import List, Dict, Any
from src.domain.product import Product
from src.domain.result import Result

class ManageStockUseCase:
    def __init__(self, repository):
        self.repository = repository

    def create_product(self, product_id: str, name: str) -> Result[None, str]:
        if self.repository.get_by_id(product_id):
            return Result.fail("Produto já cadastrado.")
        product = Product(id=product_id, name=name, quantity=0)
        self.repository.save(product)
        return Result.ok(None)

    def execute_add(self, product_id: str, amount: int, expiration_date: str, batch_code: str) -> Result[None, str]:
        product = self.repository.get_by_id(product_id)
        if not product: return Result.fail("Produto não encontrado.")
            
        res = product.add_stock(amount, expiration_date, batch_code)
        if res.is_success:
            self.repository.save(product)
            self.repository.log_transaction(product_id, f'ENTRADA (Lote {batch_code})', amount)
        return res

    def execute_remove(self, product_id: str, amount: int) -> Result[None, str]:
        product = self.repository.get_by_id(product_id)
        if not product: return Result.fail("Produto não encontrado.")
            
        res = product.remove_stock(amount)
        if res.is_success:
            self.repository.save(product)
            self.repository.log_transaction(product_id, 'SAIDA (Baixa Automática FEFO)', amount)
        return res

    def list_all(self) -> List[Product]: return self.repository.get_all()
    
    def get_picking_info(self, product_id: str) -> Result[Dict[str, Any], str]:
        product = self.repository.get_by_id(product_id)
        if not product: return Result.fail("Produto sem cadastro.")
        
        info = {
            "name": product.name,
            "total_quantity": product.quantity,
            "instructions": product.get_picking_instructions()
        }
        return Result.ok(info)

    def get_recent_history(self) -> List[Dict[str, Any]]: return self.repository.get_history()
EOF

    # 4. API Web (Novo Endpoint de Picking)
    cat << 'EOF' > app.py
from flask import Flask, jsonify, request, render_template
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.use_cases.manage_stock import ManageStockUseCase

app = Flask(__name__)
repo = SQLiteProductRepository("estoque_producao.db")
uc = ManageStockUseCase(repository=repo)

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/produtos', methods=['GET'])
def get_produtos():
    return jsonify([{
        'id': p.id, 'name': p.name, 'quantity': p.quantity
    } for p in uc.list_all()])

@app.route('/api/produto/<sku>', methods=['GET'])
def get_produto(sku):
    p = repo.get_by_id(sku)
    return jsonify({'id': p.id, 'name': p.name, 'quantity': p.quantity}) if p else (jsonify({'error': 'Not found'}), 404)

@app.route('/api/reposicao/<sku>', methods=['GET'])
def get_picking_info(sku):
    res = uc.get_picking_info(sku)
    return jsonify(res.value) if res.is_success else (jsonify({'error': res.error}), 404)

@app.route('/api/produto', methods=['POST'])
def create_produto():
    data = request.json
    res = uc.create_product(data['id'], data['name'])
    return (jsonify({'message': 'OK'}), 201) if res.is_success else (jsonify({'error': res.error}), 400)

@app.route('/api/entrada', methods=['POST'])
def add_stock():
    data = request.json
    res = uc.execute_add(data['id'], data['amount'], data.get('expiration_date', ''), data.get('batch_code', ''))
    return (jsonify({'message': 'OK'}), 200) if res.is_success else (jsonify({'error': res.error}), 400)

@app.route('/api/saida', methods=['POST'])
def remove_stock():
    data = request.json
    res = uc.execute_remove(data['id'], data['amount'])
    return (jsonify({'message': 'OK'}), 200) if res.is_success else (jsonify({'error': res.error}), 400)

@app.route('/api/historico', methods=['GET'])
def get_historico(): return jsonify(uc.get_recent_history())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
EOF

    # 5. Interface com Aba de Reposição (O cérebro do corredor)
    cat << 'EOF' > templates/index.html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Kippe-Estoque | Alta Performance</title>
    <script src="https://unpkg.com/html5-qrcode"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #eef2f5; margin: 0; padding: 15px; color: #333; }
        .card { background: white; border-radius: 12px; padding: 15px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .btn { width: 100%; padding: 14px; border: none; border-radius: 8px; font-weight: 700; font-size: 16px; margin-bottom: 10px; cursor: pointer; color: white; transition: 0.2s; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-blue { background: #007bff; }
        .btn-green { background: #28a745; }
        .btn-red { background: #dc3545; }
        .btn-orange { background: #fd7e14; }
        input { width: 100%; padding: 12px; margin: 5px 0 15px; border: 1px solid #dcdcdc; border-radius: 8px; box-sizing: border-box; font-size:16px; background: #f9f9f9;}
        #reader { width: 100%; border-radius: 12px; overflow: hidden; margin-bottom: 10px; border: none; }
        .tabs { display: flex; border-bottom: 2px solid #ddd; margin-bottom: 15px; overflow-x: auto; white-space: nowrap; }
        .tab { flex: 1; text-align: center; padding: 10px 15px; cursor: pointer; font-weight: bold; color: #888; font-size: 14px; }
        .tab.active { border-bottom: 3px solid #007bff; color: #007bff; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .list-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; font-size: 14px; }
        .badge { background: #007bff; color: white; padding: 4px 8px; border-radius: 12px; font-weight: bold; }
        .alert-box { background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin-bottom: 10px; font-size: 14px; }
    </style>
</head>
<body>
    <h2 style="text-align:center; color:#1a1a1a;">Kippe-Estoque</h2>

    <div class="card">
        <button class="btn btn-blue" onclick="startScanner()">📷 Iniciar Leitor</button>
        <div id="reader"></div>
    </div>

    <div class="card">
        <div class="tabs">
            <div class="tab active" onclick="switchTab('caixa')">Recebimento/Baixa</div>
            <div class="tab" onclick="switchTab('reposicao')">Gôndola (Reposição)</div>
            <div class="tab" onclick="switchTab('estoque')">Inventário</div>
        </div>

        <div id="caixa-tab" class="tab-content active">
            <input type="text" id="sku" placeholder="SKU LIDO" readonly>
            <input type="text" id="nome" placeholder="Nome do Produto">
            <input type="number" id="qtd" placeholder="Quantidade" value="1">
            
            <div style="display:flex; gap:10px;">
                <div style="flex:1;">
                    <label style="font-size:12px; font-weight:bold;">Lote (Obrigatório +)</label>
                    <input type="text" id="lote" placeholder="Ex: LT-24" oninput="validarCampos()">
                </div>
                <div style="flex:1;">
                    <label style="font-size:12px; font-weight:bold;">Validade (Obrigatório +)</label>
                    <input type="date" id="validade" onchange="validarCampos()">
                </div>
            </div>
            
            <div style="display: flex; gap: 10px;">
                <button class="btn btn-green" id="btn-entrada" onclick="processarTransacao('+')" disabled>+ Entrada</button>
                <button class="btn btn-red" onclick="processarTransacao('-')">- Saída (FEFO)</button>
            </div>
        </div>

        <div id="reposicao-tab" class="tab-content">
            <div id="instrucoes-reposicao">
                <p style="text-align:center; color:#666; font-size: 14px;">Para repor a gôndola, leia o código de barras do produto na prateleira para saber qual Lote buscar no depósito.</p>
            </div>
        </div>

        <div id="estoque-tab" class="tab-content">
            <button class="btn" style="background:#6c757d;" onclick="carregarEstoque()">🔄 Atualizar Inventário</button>
            <div id="lista-estoque" style="margin-top: 10px;"></div>
        </div>
    </div>

    <script>
        let html5QrcodeScanner;
        let currentTab = 'caixa';

        function playBeep() {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                osc.type = 'sine'; osc.frequency.setValueAtTime(880, ctx.currentTime);
                osc.connect(ctx.destination); osc.start(); osc.stop(ctx.currentTime + 0.1);
            } catch (e) {}
        }

        function switchTab(t) {
            currentTab = t;
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(t + '-tab').classList.add('active');
            if(t === 'estoque') carregarEstoque();
        }

        function startScanner() {
            if(html5QrcodeScanner) return;
            html5QrcodeScanner = new Html5Qrcode("reader");
            html5QrcodeScanner.start({ facingMode: "environment" }, { fps: 15, qrbox: {width: 250, height: 150} }, 
            (decodedText) => {
                playBeep(); 
                if (navigator.vibrate) navigator.vibrate(100); 
                html5QrcodeScanner.stop(); html5QrcodeScanner = null;
                
                // Roteamento inteligente baseado na aba atual
                if(currentTab === 'reposicao') {
                    gerarPickList(decodedText);
                } else {
                    document.getElementById('sku').value = decodedText;
                    verificarCadastro(decodedText);
                }
            }, (err) => {}).catch(err => alert(err));
        }

        // --- FLUXO DE REPOSIÇÃO (PICK-LIST) ---
        async function gerarPickList(sku) {
            const res = await fetch(`/api/reposicao/${sku}`);
            const div = document.getElementById('instrucoes-reposicao');
            
            if(res.status === 404) {
                div.innerHTML = `<div class="alert-box" style="border-color:#dc3545; background:#f8d7da;">Produto não encontrado no sistema.</div>`;
                return;
            }
            
            const data = await res.json();
            if(data.total_quantity === 0) {
                div.innerHTML = `<div class="alert-box" style="border-color:#dc3545; background:#f8d7da;"><b>${data.name}</b><br>Ruptura de Estoque (Estoque Zero no depósito).</div>`;
                return;
            }

            let html = `<h3>${data.name}</h3>`;
            html += `<p><b>Total no Depósito:</b> ${data.total_quantity} unidades</p>`;
            html += `<h4 style="color:#fd7e14;">Ordem de Retirada (FEFO):</h4>`;
            
            data.instructions.forEach((lote, index) => {
                html += `
                <div class="alert-box">
                    <b>${index + 1}º - Pegar do Lote: ${lote.lote}</b><br>
                    <small>Validade: ${lote.validade} | Disponível: ${lote.qtd_disponivel} un.</small>
                </div>`;
            });
            div.innerHTML = html;
        }

        // --- FLUXO DE CAIXA/DOCA ---
        async function verificarCadastro(sku) {
            const res = await fetch(`/api/produto/${sku}`);
            if(res.status === 404) document.getElementById('nome').focus();
            else {
                const data = await res.json();
                document.getElementById('nome').value = data.name;
                document.getElementById('qtd').focus();
            }
            validarCampos();
        }

        function validarCampos() {
            const skuVal = document.getElementById('sku').value;
            const loteVal = document.getElementById('lote').value;
            const dateVal = document.getElementById('validade').value;
            document.getElementById('btn-entrada').disabled = !(skuVal && loteVal && dateVal);
        }

        async function processarTransacao(operacao) {
            const sku = document.getElementById('sku').value;
            const nome = document.getElementById('nome').value;
            const qtd = parseInt(document.getElementById('qtd').value) || 0;
            const lote = document.getElementById('lote').value;
            const validade = document.getElementById('validade').value;

            if(!sku || qtd <= 0) return alert("SKU e Quantidade obrigatórios.");

            let resCheck = await fetch(`/api/produto/${sku}`);
            if(resCheck.status === 404) {
                if(!nome) return alert("Novo produto. NOME é obrigatório.");
                await fetch('/api/produto', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id: sku, name: nome})
                });
            }

            const endpoint = operacao === '+' ? '/api/entrada' : '/api/saida';
            const payload = { id: sku, amount: qtd };
            if (operacao === '+') {
                payload.expiration_date = validade;
                payload.batch_code = lote;
            }

            const resMov = await fetch(endpoint, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            if(resMov.ok) {
                document.getElementById('sku').value = '';
                document.getElementById('nome').value = '';
                document.getElementById('qtd').value = '1';
                document.getElementById('lote').value = '';
                document.getElementById('validade').value = '';
                validarCampos();
                alert("Movimentação Registrada!");
            } else {
                const data = await resMov.json();
                alert("🛑 BLOQUEIO DO SISTEMA:\n" + data.error);
            }
        }

        async function carregarEstoque() {
            const res = await fetch('/api/produtos');
            const produtos = await res.json();
            let html = '';
            produtos.forEach(p => {
                html += `<div class="list-item">
                            <span><b>${p.name}</b> <br><small style="color:#888">${p.id}</small></span>
                            <span class="badge">${p.quantity} un</span>
                         </div>`;
            });
            document.getElementById('lista-estoque').innerHTML = html;
        }
    </script>
</body>
</html>
EOF

    # 6. Testes Unitários de Regressão Extremamente Rigorosos
    cat << 'EOF' > tests/test_fefo.py
import pytest
from src.domain.product import Product
from datetime import datetime, timedelta

def test_fefo_lotes_complex_resolution():
    p = Product(id="FEFO-03", name="Refrigerante", quantity=0)
    hoje = datetime.today()
    v_curto = (hoje + timedelta(days=5)).strftime("%Y-%m-%d")
    v_longo = (hoje + timedelta(days=20)).strftime("%Y-%m-%d")

    # Recebimento na Doca
    res1 = p.add_stock(10, v_longo, "LOTE-B")
    res2 = p.add_stock(5, v_curto, "LOTE-A")
    assert res1.is_success and res2.is_success
    assert p.quantity == 15

    # Verificando Instruções de Reposição na Gôndola (Pick-List)
    instrucoes = p.get_picking_instructions()
    assert instrucoes[0]['lote'] == "LOTE-A" # Deve ser o primeiro a sair
    assert instrucoes[1]['lote'] == "LOTE-B"

    # Baixa no Caixa
    res_baixa = p.remove_stock(7)
    assert res_baixa.is_success
    assert p.quantity == 8
    
    # O LOTE-A (5 un) deve ter sumido e o LOTE-B deve ter sido abatido em 2 un (10-2=8)
    assert "LOTE-A" not in p.batches
    assert p.batches["LOTE-B"]['qty'] == 8
EOF

    echo -e "\n[!] Executando validação de regressão do Motor FEFO c/ Pick-List...\n"
    python -m pytest tests/test_fefo.py -v
    TEST_STATUS=$?

} 2>&1 | tee "$LOG_FILE"

FINAL_STATUS=${PIPESTATUS[0]}

if [ $FINAL_STATUS -eq 0 ]; then
    echo -e "\n[OK] FEFO Otimizado e Pick-List de Gôndola implementados com sucesso!"
    
    cat << 'EOF' > ESTADO_PROJETO.md
# 📦 Kippe-Estoque Core: Master Roadmap Institucional

## 1. Visão Geral
* **Objetivo:** Controle logístico WMS, prevenção de rupturas e falhas sanitárias.
* **Arquitetura:** Clean Architecture, Algoritmo FEFO no Core, RESTful API (Flask).
* **Ambiente:** Termux Server (Galaxy A50) + Client HTML5.

## 2. Roadmap de Engenharia (Sprints)
* [x] Sprints 001 a 007: Core O(1), Repositório SQLite, API Web, Scanner HTML5 e Audit Trail.

### FASE 4: Governança & Segurança Logística (Atual)
* [x] **Sprint 008 (V2):** FEFO Institucional. Adicionado controle estrito de `Lotes` e Aba de Reposição (Pick-List), gerando rotas autônomas de retirada de depósito baseadas na data de vencimento.
* [ ] **Sprint 009:** Autenticação de Operador (Sistema de PIN numérico no Audit Trail).

### FASE 5: Inteligência de Negócio & Relatórios (A Fazer)
* [ ] **Sprint 010:** Dashboard Analítico (Alerta de ruptura de estoque).
* [ ] **Sprint 011:** Exportação de Dados (CSV das movimentações).
EOF

    git add .
    git commit -m "feat(domain): adiciona controle por lote e pick-list wms via aba de reposição"
    git push 
else
    echo -e "\n[FALHA] Validação recusada. Analise os erros."
fi

