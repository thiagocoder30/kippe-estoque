import os
import sqlite3
import traceback
from datetime import datetime
from flask import Flask, jsonify, request, render_template
from src.infrastructure.container import Container
from src.services.dashboard_projection import DashboardReadModel

# Caminho absoluto para o banco (Blinda contra quedas do Servidor)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'kippe.db')

container = Container()
app = Flask(__name__)
app.secret_key = getattr(container.config, 'SECRET_KEY', 'kippe_enterprise_key')

# Proteção global contra falhas silenciosas
@app.errorhandler(Exception)
def handle_exception(e):
    err = traceback.format_exc()
    print(f"[CRÍTICO] Falha capturada globalmente:\n{err}")
    return jsonify({"error": "Erro Interno do Servidor", "details": str(e)}), 500

@app.route('/')
def index(): 
    return render_template('index.html')

@app.route('/api/auth/me', methods=['GET'])
def me():
    return jsonify({'authenticated': True, 'operator': {'id': 'ADMIN', 'name': 'ADMIN', 'role': 'ADMIN'}})

# Mapeando todas as rotas possíveis que o Frontend pode chamar (Aliases)
@app.route('/api/produto/<path:sku>', methods=['GET'])
@app.route('/api/produtos/<path:sku>', methods=['GET'])
@app.route('/api/sku/<path:sku>', methods=['GET'])
def get_produto(sku):
    try:
        dashboard = DashboardReadModel.get_product_dashboard(sku)
        if dashboard:
            return jsonify(dashboard), 200
            
        # Fallback de emergência (caso o produto exista apenas na entidade raiz)
        p = container.product_repository.get_by_id(sku)
        if p:
            return jsonify({'id': p.id, 'name': p.name, 'quantity': p.quantity}), 200
            
        return jsonify({'error': 'Produto não encontrado.'}), 404
    except Exception as e:
        print(f"ERRO API /produto/<sku>: {traceback.format_exc()}")
        return jsonify({'error': 'Falha na leitura do banco', 'details': str(e)}), 500

# MÓDULO FEFO INSTITUCIONAL (Blindado com Caminho Absoluto)
@app.route('/api/relatorios/vencimentos', methods=['GET'])
def get_fefo_reports():
    try:
        if not os.path.exists(DB_PATH):
            return jsonify([{"sku": "DB-ERR", "name": "BANCO DE DADOS AUSENTE", "expiration": f"Caminho falhou: {DB_PATH}", "batch": "CRASH"}]), 200

        conn = sqlite3.connect(DB_PATH)
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
                
                if dias > 60:
                    continue
                    
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
                continue
                
        result.sort(key=lambda x: x['sort_days'])
        for item in result: 
            if 'sort_days' in item:
                del item['sort_days']
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"CRASH FEFO: {traceback.format_exc()}")
        return jsonify([{"sku": "SYS-ERR", "name": "ERRO NO SERVIDOR", "expiration": str(e), "batch": "CRASH"}]), 200

@app.route('/api/entrada', methods=['POST'])
def entrada():
    return jsonify({"status": "pendente_dev001_2"})
    
# Tratador de Rotas Faltantes (Para não quebrar a tela de forma silenciosa)
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Rota não encontrada"}), 404

if __name__ == '__main__':
    is_dev = (getattr(container.config, 'ENV', 'production') == 'development')
    app.run(host=getattr(container.config, 'HOST', '0.0.0.0'), port=getattr(container.config, 'PORT', 8000), debug=is_dev)
