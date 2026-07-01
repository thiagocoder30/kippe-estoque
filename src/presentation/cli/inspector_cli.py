import os
import subprocess
from src.infrastructure.inspection.scanner import DynamicCapabilityEngine, Capability, OperationalKPIs

def get_project_root() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], 
            text=True, stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError:
        return os.getcwd()

def print_dynamic_matrix(capabilities: list[Capability]):
    C_RESET, C_BOLD, C_CYAN = '\033[0m', '\033[1m', '\033[96m'
    C_GREEN, C_YELLOW, C_RED = '\033[92m', '\033[93m', '\033[91m'

    print(f"\n{C_BOLD}CAPABILITY MATRIX (OPERATIONAL QUESTIONS){C_RESET}")
    print(f"{C_CYAN}-------------------------------------------------------------------------{C_RESET}")
    print(f"{'Pergunta Operacional (Capacidade)'.ljust(50)} | {'Score'} | {'SLA (ms)'}")
    print(f"{C_CYAN}-------------------------------------------------------------------------{C_RESET}")
    
    for cap in capabilities:
        score = cap.total_score
        if score >= 90:
            status = f"{C_GREEN}{score}%{C_RESET}"
        elif score >= 50:
            status = f"{C_YELLOW}{score}%{C_RESET}"
        else:
            status = f"{C_RED}{score}%{C_RESET}"
            
        latency = f"{cap.latency_ms:.1f} ms" if cap.latency_ms > 0 else "N/A"
        print(f"{cap.question.ljust(50)} | {status.ljust(14)} | {latency}")
    print(f"{C_CYAN}-------------------------------------------------------------------------{C_RESET}\n")

def print_operational_kpis(kpis: OperationalKPIs):
    C_RESET, C_BOLD, C_CYAN = '\033[0m', '\033[1m', '\033[96m'
    C_GREEN, C_YELLOW, C_RED = '\033[92m', '\033[93m', '\033[91m'
    
    health_color = C_GREEN if kpis.health_score > 90 else C_YELLOW
    trust_color = C_GREEN if kpis.avg_trust_score > 90 else C_YELLOW
    crit_color = C_RED if kpis.critical_skus > 0 else C_GREEN

    print(f"{C_BOLD}OPERATIONAL KPIs (COMMAND CENTER){C_RESET}")
    print(f"{C_CYAN}========================================={C_RESET}")
    print(f"Health do Estoque ........... {health_color}{kpis.health_score:.1f}%{C_RESET}")
    print(f"{C_CYAN}-----------------------------------------{C_RESET}")
    print(f"SKUs Críticos ............... {crit_color}{kpis.critical_skus}{C_RESET}")
    print(f"{C_CYAN}-----------------------------------------{C_RESET}")
    print(f"Produtos Vencendo (<30d) .... {C_YELLOW}{kpis.expiring_soon}{C_RESET}")
    print(f"{C_CYAN}-----------------------------------------{C_RESET}")
    print(f"Trust Score Global .......... {trust_color}{kpis.avg_trust_score:.1f}%{C_RESET}")
    print(f"{C_CYAN}-----------------------------------------{C_RESET}")
    print(f"Produtos sem giro ........... {C_YELLOW}{kpis.stagnant_skus}{C_RESET}")
    print(f"{C_CYAN}========================================={C_RESET}\n")

if __name__ == "__main__":
    engine = DynamicCapabilityEngine()
    
    print("\n\033[90m[+] Avaliando Níveis Estruturais, Comportamentais e Operacionais...\033[0m")
    capabilities = engine.evaluate_all()
    
    print("\033[90m[+] Extraindo Inteligência do Event Store...\033[0m")
    kpis = engine.generate_kpis()
    
    print_dynamic_matrix(capabilities)
    print_operational_kpis(kpis)
