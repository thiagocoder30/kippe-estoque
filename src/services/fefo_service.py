import sqlite3
import logging
from datetime import datetime
from typing import List, Dict

# Configuração Enterprise de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FefoEnterpriseService:
    def __init__(self, db_path: str = "kippe.db"):
        self.db_path = db_path

    def get_critical_batches(self) -> List[Dict]:
        logging.info(f"[*] Iniciando Varredura FEFO no banco: {self.db_path}")
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # 1. Introspecção do Banco (Descobre as tabelas reais)
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r['name'] for r in cursor.fetchall()]
                logging.info(f"[*] Tabelas encontradas: {tables}")

                result = []
                today = datetime.now()

                # Estratégia 1: Tabela de Lotes (Enterprise Padrão)
                if 'batches' in tables:
                    logging.info("[*] Tabela 'batches' localizada. Extraindo dados...")
                    query = '''
                        SELECT b.batch_code as batch, b.expiration_date, p.name, p.id as sku
                        FROM batches b
                        LEFT JOIN products p ON b.product_id = p.id
                        WHERE b.expiration_date IS NOT NULL AND b.expiration_date != ''
                    '''
                    rows = cursor.execute(query).fetchall()
                    for r in rows:
                        result.append({
                            "sku": r['sku'] if r['sku'] else "N/A",
                            "name": r['name'] if r['name'] else "PRODUTO DESCONHECIDO",
                            "expiration_date": r['expiration_date'],
                            "batch": r['batch']
                        })

                # Estratégia 2: Fallback para a Tabela de Produtos
                if not result and 'products' in tables:
                    logging.info("[*] Varrendo tabela 'products' por datas de validade...")
                    cursor.execute("PRAGMA table_info(products)")
                    cols = [c['name'] for c in cursor.fetchall()]
                    
                    if 'expiration_date' in cols:
                        rows = cursor.execute("SELECT id as sku, name, expiration_date FROM products WHERE expiration_date IS NOT NULL AND expiration_date != ''").fetchall()
                        for r in rows:
                            result.append({
                                "sku": r['sku'],
                                "name": r['name'],
                                "expiration_date": r['expiration_date'],
                                "batch": "LOTE ÚNICO"
                            })
                    else:
                        # PROVA DE VIDA (Para garantir que o banco está conectado mesmo sem datas)
                        logging.warning("[!] Coluna expiration_date não encontrada. Retornando amostra de prova de vida.")
                        rows = cursor.execute("SELECT id, name, quantity FROM products LIMIT 5").fetchall()
                        return [{"sku": str(r["id"]), "name": f"SALDO: {r['quantity']} UN | {r['name']}", "expiration": "CONEXÃO OK - SEM DATA", "batch": "PROVA DE VIDA"} for r in rows]

                if not result:
                    return [{"sku": "INFO", "name": "BANCO CONECTADO, MAS SEM PRODUTOS COM VALIDADE", "expiration": "VERIFIQUE O CADASTRO", "batch": "SYS"}]

                # 2. Motor de Regras de Negócio FEFO
                fefo_report = []
                for item in result:
                    try:
                        # Parse robusto de data (YYYY-MM-DD)
                        date_str = item['expiration_date'].split(' ')[0]
                        exp_date = datetime.strptime(date_str, '%Y-%m-%d')
                        days_left = (exp_date - today).days

                        status = "🔴 CRÍTICO" if days_left <= 30 else ("🟠 ALERTA" if days_left <= 60 else "🟡 ATENÇÃO")

                        fefo_report.append({
                            "sku": str(item['sku']),
                            "name": f"{status} | {item['name']}",
                            "expiration": f"{date_str} ({days_left} DIAS)",
                            "batch": str(item['batch'])
                        })
                    except Exception as e:
                        logging.error(f"Erro ao calcular data do SKU {item['sku']}: {e}")
                        fefo_report.append({
                            "sku": str(item['sku']),
                            "name": f"⚪ FORMATO INVÁLIDO | {item['name']}",
                            "expiration": str(item['expiration_date']),
                            "batch": str(item['batch'])
                        })

                # Ordena pelo produto que vence primeiro
                return sorted(fefo_report, key=lambda x: x['expiration'])

        except sqlite3.Error as e:
            logging.error(f"Erro SQL fatal: {e}")
            return [{"sku": "SQL-ERR", "name": "FALHA NO BANCO DE DADOS", "expiration": str(e), "batch": "CRITICAL"}]
        except Exception as e:
            logging.error(f"Erro genérico fatal: {e}")
            return [{"sku": "SYS-ERR", "name": "FALHA NO SERVIÇO FEFO", "expiration": str(e), "batch": "CRITICAL"}]
