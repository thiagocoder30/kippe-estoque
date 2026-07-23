import os
import sqlite3
import traceback
from typing import Optional, Dict, Any

# Resolve o caminho absoluto do banco de dados (Garante que nunca crie um DB fantasma)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DB_PATH = os.path.join(BASE_DIR, 'kippe.db')

class DashboardReadModel:
    @staticmethod
    def get_product_dashboard(sku_or_barcode: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(DB_PATH):
            print(f"[CRÍTICO] Banco de dados não encontrado no caminho: {DB_PATH}")
            return None
            
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            # 1. Catálogo (Busca Dupla: SKU ou CÓDIGO DE BARRAS)
            cur.execute("SELECT * FROM catalog WHERE sku = ? OR barcode = ?", (sku_or_barcode, sku_or_barcode))
            cat_row = cur.fetchone()
            
            if not cat_row:
                conn.close()
                return None
                
            cat = dict(cat_row)
            true_sku = cat.get('sku', sku_or_barcode)
            
            # 2. Lotes e Saldos
            cur.execute("SELECT * FROM batches WHERE sku = ?", (true_sku,))
            batches_rows = cur.fetchall()
            
            batches = []
            total_quantity = 0
            primary_supplier = "N/D"
            
            for b in batches_rows:
                b_dict = dict(b)
                qty = int(b_dict.get('quantity') or 0)
                store_qty = int(b_dict.get('quantity_store') or 0)
                bal_qty = int(b_dict.get('store_balance') or 0)
                
                batches.append({
                    "batch_code": b_dict.get('batch_code', 'N/D'),
                    "quantity": qty,
                    "expiration_date": b_dict.get('expiration', 'N/D')
                })
                total_quantity += (qty + store_qty + bal_qty)
                
                if b_dict.get('supplier') and b_dict.get('supplier') != 'None' and primary_supplier == "N/D":
                    primary_supplier = b_dict.get('supplier')
                    
            # 3. Auditoria (Histórico)
            cur.execute("SELECT * FROM audit_log WHERE sku = ? ORDER BY timestamp DESC LIMIT 10", (true_sku,))
            audit_rows = cur.fetchall()
            
            audit_logs = []
            for a in audit_rows:
                a_dict = dict(a)
                audit_logs.append({
                    "date": a_dict.get('timestamp', ''),
                    "op": a_dict.get('operation', ''),
                    "qty": a_dict.get('quantity', 0),
                    "operator": a_dict.get('operator', 'SISTEMA')
                })
                
            conn.close()
            
            return {
                "sku": true_sku,
                "description": cat.get('description', 'PRODUTO SEM NOME'),
                "barcode": cat.get('barcode', true_sku),
                "category": cat.get('category', 'N/D'),
                "photo": cat.get('photo', None),
                "balances": {
                    "total": total_quantity
                },
                "primary_supplier": primary_supplier,
                "physical_location": {
                    "details": cat.get('box_location', 'NÃO ENDEREÇADO')
                },
                "traceability": {
                    "batches": batches
                },
                "audit_logs": audit_logs
            }
            
        except Exception as e:
            print(f"Erro no Read Model do sku/ean {sku_or_barcode}: {traceback.format_exc()}")
            return None
