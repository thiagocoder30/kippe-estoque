import os

print("[*] Iniciando a Sprint DEV001.1 - Injeção da Camada de Projeção (CQRS)...")

# Localiza dinamicamente onde o repositório está salvo no seu projeto
targets = [
    'src/interfaces/sqlite_repository.py',
    'src/infrastructure/sqlite_repository.py',
    'src/infrastructure/repositories/sqlite_product_repository.py'
]

target_file = None
for t in targets:
    if os.path.exists(t):
        target_file = t
        break

if not target_file:
    print("[-] Arquivo do repositório não encontrado. Abortando para segurança.")
    exit(1)

with open(target_file, 'r', encoding='utf-8') as f:
    content = f.read()

# O novo método de Read Model que lê direto do banco e monta o DTO da UI
novo_metodo = """
    def get_dashboard_projection(self, sku: str) -> dict:
        import sqlite3
        try:
            conn = sqlite3.connect('kippe.db')
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            # 1. Catálogo
            cur.execute("SELECT * FROM catalog WHERE sku = ?", (sku,))
            catalog_row = cur.fetchone()
            
            if not catalog_row:
                conn.close()
                return None
                
            catalog_data = dict(catalog_row)
            
            # 2. Lotes e Saldos
            cur.execute("SELECT * FROM batches WHERE sku = ?", (sku,))
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
                
                if b_dict.get('supplier') and primary_supplier == "N/D":
                    primary_supplier = b_dict.get('supplier')
                    
            # 3. Auditoria (Últimas Movimentações)
            cur.execute("SELECT * FROM audit_log WHERE sku = ? ORDER BY timestamp DESC LIMIT 10", (sku,))
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
            
            # 4. Retorna O Contrato Exato esperado pela UI
            return {
                "sku": sku,
                "description": catalog_data.get('description', 'PRODUTO SEM NOME'),
                "barcode": catalog_data.get('barcode', sku),
                "category": catalog_data.get('category', 'N/D'),
                "photo": catalog_data.get('photo', None),
                "balances": {
                    "total": total_quantity
                },
                "primary_supplier": primary_supplier,
                "physical_location": {
                    "details": catalog_data.get('box_location', 'NÃO ENDEREÇADO')
                },
                "traceability": {
                    "batches": batches
                },
                "audit_logs": audit_logs
            }
            
        except Exception as e:
            print(f"Erro no Read Model do sku {sku}: {e}")
            return None
"""

if "def get_dashboard_projection" not in content:
    content += "\n" + novo_metodo
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[+] Projection Method injetado com sucesso no {target_file}!")
else:
    print("[!] O método get_dashboard_projection já existe neste repositório.")

