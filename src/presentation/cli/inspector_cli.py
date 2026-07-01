import os
import subprocess
from typing import Dict, List
from src.infrastructure.inspection.scanner import CapabilityScanner, CapabilityTarget

def get_project_root() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], 
            text=True, stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError:
        return os.getcwd()

def print_inspector_report(capabilities: Dict[str, List[CapabilityTarget]]):
    C_RESET, C_BOLD, C_CYAN = '\033[0m', '\033[1m', '\033[96m'
    C_GREEN, C_RED, C_YELLOW = '\033[92m', '\033[91m', '\033[93m'

    print(f"\n{C_CYAN}========================================={C_RESET}")
    print(f"{C_BOLD}KIPPE CAPABILITY INSPECTOR               {C_RESET}")
    print(f"{C_CYAN}========================================={C_RESET}\n")

    for category, targets in capabilities.items():
        print(f"{C_BOLD}{category}{C_RESET}\n")
        for target in targets:
            marker = f"{C_GREEN}✓{C_RESET}" if target.is_met else f"{C_RED}✗{C_RESET}"
            print(f"  {marker} {target.name}")
        print("")

    print(f"{C_CYAN}========================================={C_RESET}")

def print_capability_matrix(capabilities: Dict[str, List[CapabilityTarget]]):
    C_RESET, C_BOLD, C_CYAN = '\033[0m', '\033[1m', '\033[96m'
    
    # Mapeamento estático para a demonstração da progressão do Programa F
    matrix = [
        ("Consulta SKU", 100),
        ("Busca Textual", 0),
        ("Dashboard", 0),
        ("Compras (Reposição)", 70),
        ("Validade (SmartSheet)", 85),
        ("Auditoria de Divergências", 95),
        ("Relatórios Executivos", 0)
    ]

    print(f"\n{C_BOLD}CAPABILITY MATRIX (PROGRAM F PROGRESSION){C_RESET}")
    print(f"{C_CYAN}-----------------------------------------{C_RESET}")
    print(f"{'Capacidade'.ljust(25)} | {'Status / Maturidade'}")
    print(f"{C_CYAN}-----------------------------------------{C_RESET}")
    
    for cap, score in matrix:
        if score == 100:
            status = f"\033[92m✅ {score}%\033[0m"
        elif score == 0:
            status = f"\033[91m❌ {score}%\033[0m"
        else:
            status = f"\033[93m⏳ {score}%\033[0m"
        print(f"{cap.ljust(25)} | {status}")
    print(f"{C_CYAN}-----------------------------------------{C_RESET}\n")

def print_operational_questions():
    C_RESET, C_BOLD, C_YELLOW = '\033[0m', '\033[1m', '\033[93m'
    
    questions = [
        "Quanto tenho deste SKU? (Onde ele está?)",
        "Qual lote devo vender primeiro?",
        "O que vence esta semana?",
        "O que preciso comprar hoje?",
        "Quais produtos estão parados há muito tempo?",
        "Qual produto perdeu confiança operacional?",
        "Quanto dinheiro está parado no estoque?"
    ]

    print(f"{C_BOLD}OPERATIONAL QUESTIONS (TARGETS){C_RESET}")
    print(f"{C_YELLOW}-----------------------------------------{C_RESET}")
    for q in questions:
        print(f" 🎯 {q}")
    print(f"{C_YELLOW}========================================={C_RESET}\n")

if __name__ == "__main__":
    root_dir = get_project_root()
    scanner = CapabilityScanner(root_dir)
    results = scanner.scan()
    
    print_inspector_report(results)
    print_capability_matrix(results)
    print_operational_questions()
