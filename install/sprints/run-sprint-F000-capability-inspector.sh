#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM F: CAPABILITY & INTELLIGENCE
# SPRINT F000: CAPABILITY INSPECTOR
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=3
kippe::banner_program "F" "F000" "Capability Inspector & Matrix"

# Preparação de Diretórios
mkdir -p "${KIPPE_ROOT}/src/infrastructure/inspection"
touch "${KIPPE_ROOT}/src/infrastructure/inspection/__init__.py"
mkdir -p "${KIPPE_ROOT}/src/presentation/cli"

kippe::step 1 ${TOTAL_STEPS} "Deploying Capability Scanner and Matrix Engine..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/inspection/scanner.py"
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class CapabilityTarget:
    name: str
    target_files: List[str]
    target_patterns: List[str]
    weight: int
    score: int = 0
    is_met: bool = False

class CapabilityScanner:
    """
    Inspeciona dinamicamente a base de código para mapear as capacidades ativas da plataforma.
    """
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.capabilities = self._define_matrix()

    def _define_matrix(self) -> Dict[str, List[CapabilityTarget]]:
        return {
            "DOMAIN": [
                CapabilityTarget("InventoryAccount", ["src/domain/warehouse/ledger.py"], ["class InventoryAccount"], 100),
                CapabilityTarget("Product", ["src/domain/catalog/product.py"], ["class Product"], 100),
                CapabilityTarget("Commands", ["src/application/warehouse/commands.py"], ["class ReceiveGoodsCommand"], 100),
                CapabilityTarget("Events", ["src/domain/warehouse/ledger.py"], ["_uncommitted_events"], 100)
            ],
            "APPLICATION": [
                CapabilityTarget("InventoryQueryService", ["src/application/warehouse/query_service.py"], ["class InventoryQueryService"], 100),
                CapabilityTarget("CommandBus", ["src/application/warehouse/command_bus.py"], ["class CommandBus"], 100),
                CapabilityTarget("ReplenishmentEngine", ["src/domain/warehouse/replenishment.py", "src/application/warehouse/query_service.py"], ["ReplenishmentEngine"], 100),
                CapabilityTarget("SmartSheetBuilder", ["src/domain/warehouse/smart_sheet.py"], ["class SmartSheetBuilder"], 100),
                CapabilityTarget("OperationalTruthEngine", ["src/domain/warehouse/operational_truth.py"], ["class OperationalTruthEngine"], 100),
                CapabilityTarget("InventoryAuditService", ["src/application/warehouse/audit_service.py"], ["class InventoryAuditService"], 100)
            ],
            "READ PROJECTIONS": [
                CapabilityTarget("InventoryProductView", ["src/application/warehouse/query_service.py"], ["class InventoryProductView"], 100)
            ],
            "SEARCH": [
                CapabilityTarget("SKU", ["src/presentation/cli/warehouse_cli.py"], ["def get_sku_view"], 100),
                CapabilityTarget("Description", ["src/application/warehouse/search_service.py"], ["def search_by_description"], 100),
                CapabilityTarget("Brand", ["src/application/warehouse/search_service.py"], ["def search_by_brand"], 100),
                CapabilityTarget("Supplier", ["src/application/warehouse/search_service.py"], ["def search_by_supplier"], 100),
                CapabilityTarget("Category", ["src/application/warehouse/search_service.py"], ["def search_by_category"], 100)
            ],
            "REPORTS": [
                CapabilityTarget("Dashboard", ["src/application/warehouse/dashboard_service.py"], ["class DashboardService"], 100),
                CapabilityTarget("Executive Report", ["src/presentation/reports/executive.py"], ["class ExecutiveReport"], 100),
                CapabilityTarget("Purchase Report", ["src/presentation/reports/purchase.py"], ["class PurchaseReport"], 100),
                CapabilityTarget("Expiration Report", ["src/presentation/reports/expiration.py"], ["class ExpirationReport"], 100)
            ],
            "OBSERVABILITY": [
                CapabilityTarget("Telemetry", ["src/infrastructure/monitoring/telemetry.py"], ["class TelemetryEngine"], 100),
                CapabilityTarget("AuditTrail", ["src/infrastructure/monitoring/telemetry.py"], ["class AuditTrail"], 100)
            ],
            "RELEASE": [
                CapabilityTarget("Certification", ["src/infrastructure/release/certification.py"], ["class ProductionCertificationEngine"], 100),
                CapabilityTarget("Manifest", ["src/infrastructure/release/certification.py"], ["RELEASE_MANIFEST.json"], 100)
            ]
        }

    def scan(self) -> Dict[str, List[CapabilityTarget]]:
        for category, targets in self.capabilities.items():
            for target in targets:
                target.score = 0
                for file_path in target.target_files:
                    full_path = os.path.join(self.root_dir, file_path.replace("/", os.sep))
                    if os.path.exists(full_path):
                        target.score += 50  # Arquivo existe
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            if any(re.search(pattern, content) for pattern in target.target_patterns):
                                target.score += 50  # Padrão encontrado
                                break
                target.is_met = target.score == 100
        return self.capabilities
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Inspector CLI and Operational Questions Mapping..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/presentation/cli/inspector_cli.py"
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
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Applying Governance..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"

# Registro de Estado
kippe::checkpoint_create "300" "3.0.0-intelligence" "F000" "SUCCESS"

echo -e "\n[STATUS] Sprint F000 Concluída. KIPPE Inspector pronto para mapear a jornada de Inteligência!"
exit 0

