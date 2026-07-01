import os
import subprocess
import time
from src.infrastructure.persistence.json.ledger_repository import JsonLinesLedgerRepository
from src.infrastructure.persistence.json.product_catalog import JsonProductCatalog
from src.application.warehouse.projections.engine import ProjectionEngine

def get_project_root() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        return os.getcwd()

def format_currency(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def print_dashboard(inv_proj, exp_proj, pur_proj, load_time_ms):
    C_RESET, C_BOLD, C_CYAN = '\033[0m', '\033[1m', '\033[96m'
    C_GREEN, C_YELLOW, C_RED = '\033[92m', '\033[93m', '\033[91m'

    print(f"\n{C_CYAN}==========================================={C_RESET}")
    print(f"{C_BOLD}KIPPE OPERATIONAL DASHBOARD                {C_RESET}")
    print(f"{C_CYAN}==========================================={C_RESET}\n")

    print(f"SKUs cadastrados............. {inv_proj.total_skus}")
    print(f"Itens em estoque............. {C_BOLD}{inv_proj.total_items}{C_RESET}")
    print(f"Valor estimado............... {C_GREEN}{format_currency(inv_proj.estimated_value)}{C_RESET}")
    
    trust_color = C_GREEN if inv_proj.avg_trust_score >= 95 else (C_YELLOW if inv_proj.avg_trust_score >= 80 else C_RED)
    print(f"Trust Score Médio............ {trust_color}{inv_proj.avg_trust_score}%{C_RESET}\n")

    crit_color = C_RED if inv_proj.critical_skus_count > 0 else C_GREEN
    print(f"Produtos críticos............ {crit_color}{inv_proj.critical_skus_count}{C_RESET}")
    
    rep_urgent_cnt = len(pur_proj.urgent_replenishment)
    rep_color = C_YELLOW if rep_urgent_cnt > 0 else C_GREEN
    print(f"Reposição urgente............ {rep_color}{rep_urgent_cnt}{C_RESET}")
    
    exp_7_cnt = len(exp_proj.expiring_in_7_days)
    exp_7_color = C_YELLOW if exp_7_cnt > 0 else C_GREEN
    print(f"Vencem em 7 dias............. {exp_7_color}{exp_7_cnt}{C_RESET}")

    exp_expired_cnt = len(exp_proj.already_expired)
    exp_expired_color = C_RED if exp_expired_cnt > 0 else C_GREEN
    print(f"Vencidos..................... {exp_expired_color}{exp_expired_cnt}{C_RESET}\n")

    print(f"{C_CYAN}-------------------------------------------{C_RESET}")
    print(f"{C_BOLD}TOP CRÍTICOS{C_RESET}")
    print(f"{C_CYAN}-------------------------------------------{C_RESET}")
    
    if not inv_proj.top_critical_skus:
        print(f"{C_GREEN}✓ Operação 100% Saudável. Nenhum SKU crítico.{C_RESET}")
    else:
        for item in inv_proj.top_critical_skus[:5]:
            marker = f"{C_RED}⚠{C_RESET}" if item["priority"] == "CRITICAL" else f"{C_YELLOW}⚠{C_RESET}"
            print(f"{marker} {item['description']} ({item['sku']})")
            print(f"  └─ {item['reason']}")

    print(f"\n{C_CYAN}-------------------------------------------{C_RESET}")
    print(f"{C_BOLD}AÇÕES PARA HOJE{C_RESET}")
    print(f"{C_CYAN}-------------------------------------------{C_RESET}")

    has_actions = False
    if rep_urgent_cnt > 0:
        print(f" ✓ Comprar: {rep_urgent_cnt} SKUs com ruptura iminente.")
        has_actions = True
    if exp_expired_cnt > 0:
        print(f" ✓ Baixar Perdas: {exp_expired_cnt} SKUs vencidos no estoque.")
        has_actions = True
    if exp_7_cnt > 0:
        print(f" ✓ Promover/Transferir: {exp_7_cnt} SKUs vencem esta semana.")
        has_actions = True
    if inv_proj.critical_skus_count > 0:
        print(f" ✓ Conferir/Auditar: {inv_proj.critical_skus_count} SKUs com divergência severa.")
        has_actions = True
        
    if not has_actions:
        print(f" ✓ Nenhuma ação corretiva pendente. Operação fluída.")

    print(f"{C_CYAN}==========================================={C_RESET}")
    print(f"\033[90mProjeções carregadas em {load_time_ms:.1f} ms via CQRS Single-Pass\033[0m")
    print("")

if __name__ == "__main__":
    root_dir = get_project_root()
    
    catalog_path = os.path.join(root_dir, "data/catalog/products.json")
    ledger_path = os.path.join(root_dir, "data/ledger/events.jsonl")
    
    # Tolerância a falhas para primeira execução (cria arquivos vazios se não existirem)
    os.makedirs(os.path.dirname(catalog_path), exist_ok=True)
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    if not os.path.exists(catalog_path): open(catalog_path, 'w').write("{}")
    if not os.path.exists(ledger_path): open(ledger_path, 'w').close()
    
    catalog_repo = JsonProductCatalog(catalog_path)
    ledger_repo = JsonLinesLedgerRepository(ledger_path)
    
    engine = ProjectionEngine(ledger_repo, catalog_repo)
    
    start = time.time()
    inv_proj, exp_proj, pur_proj = engine.build_all()
    load_time_ms = (time.time() - start) * 1000
    
    print_dashboard(inv_proj, exp_proj, pur_proj, load_time_ms)
