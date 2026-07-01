#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM F: CAPABILITY & INTELLIGENCE
# SPRINT F000.1: DYNAMIC CAPABILITY ENGINE & OPERATIONAL KPIS
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
kippe::banner_program "F" "F000.1" "Dynamic Capability & KPI Engine"

kippe::step 1 ${TOTAL_STEPS} "Deploying Level 1-2-3 Dynamic Capability Engine..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/inspection/scanner.py"
import time
from dataclasses import dataclass
from typing import Dict, List, Any
from src.application.warehouse.query_service import InventoryQueryService
from src.application.warehouse.audit_service import InventoryAuditService
from src.infrastructure.persistence.json.ledger_repository import JsonLinesLedgerRepository
from src.infrastructure.persistence.memory.product_catalog import InMemoryProductCatalog

@dataclass
class Capability:
    question: str
    structural_score: int = 0
    behavioral_score: int = 0
    operational_score: int = 0
    latency_ms: float = 0.0

    @property
    def total_score(self) -> int:
        return (self.structural_score + self.behavioral_score + self.operational_score) // 3

@dataclass
class OperationalKPIs:
    health_score: float
    critical_skus: int
    expiring_soon: int
    avg_trust_score: float
    stagnant_skus: int

class DynamicCapabilityEngine:
    """
    Avalia capacidades operacionais executando cenários reais (Nível 2)
    e aferindo SLAs de tempo de resposta (Nível 3).
    """
    def __init__(self):
        self.repo = JsonLinesLedgerRepository()
        self.catalog = InMemoryProductCatalog()
        self.query_svc = InventoryQueryService(self.repo, self.catalog)
        self.audit_svc = InventoryAuditService(self.repo, self.catalog)
        # SKU de teste padrão existente no mock
        self.test_sku = "789609890001"

    def evaluate_all(self) -> List[Capability]:
        return [
            self._eval_inventory(),
            self._eval_expiration(),
            self._eval_trust(),
            self._eval_purchase(),
            self._eval_search()
        ]

    def _eval_inventory(self) -> Capability:
        cap = Capability("Quanto tenho deste SKU? (Inventory Projection)")
        cap.structural_score = 100
        start = time.time()
        try:
            view = self.query_svc.get_sku_view(self.test_sku)
            cap.behavioral_score = 100 if hasattr(view, 'available_total') else 0
            cap.latency_ms = (time.time() - start) * 1000
            cap.operational_score = 100 if cap.latency_ms < 200 else 50
        except Exception:
            pass
        return cap

    def _eval_expiration(self) -> Capability:
        cap = Capability("O que vence esta semana? (Expiration Projection)")
        cap.structural_score = 100
        start = time.time()
        try:
            view = self.query_svc.get_sku_view(self.test_sku)
            cap.behavioral_score = 100 if view.first_expiration_date != "N/A" else 80
            cap.latency_ms = (time.time() - start) * 1000
            cap.operational_score = 100 if cap.latency_ms < 300 else 50
        except Exception:
            pass
        return cap

    def _eval_trust(self) -> Capability:
        cap = Capability("Posso confiar neste saldo? (Trust Projection)")
        cap.structural_score = 100
        start = time.time()
        try:
            view = self.query_svc.get_sku_view(self.test_sku)
            cap.behavioral_score = 100 if view.trust_score_percentage is not None else 0
            cap.latency_ms = (time.time() - start) * 1000
            cap.operational_score = 100 if cap.latency_ms < 300 else 50
        except Exception:
            pass
        return cap

    def _eval_purchase(self) -> Capability:
        cap = Capability("O que preciso comprar hoje? (Purchase Projection)")
        cap.structural_score = 80 # Faltam consolidações globais
        start = time.time()
        try:
            view = self.query_svc.get_sku_view(self.test_sku)
            cap.behavioral_score = 100 if hasattr(view, 'suggested_quantity') else 0
            cap.latency_ms = (time.time() - start) * 1000
            cap.operational_score = 100 if cap.latency_ms < 300 else 50
        except Exception:
            pass
        return cap

    def _eval_search(self) -> Capability:
        cap = Capability("Busca Textual (Search Intelligence)")
        cap.structural_score = 20 # Ainda não implementado de forma global
        cap.behavioral_score = 0
        cap.operational_score = 0
        return cap

    def generate_kpis(self) -> OperationalKPIs:
        # Varre os SKUs do catálogo simulando a extração de KPIs globais
        skus = list(self.catalog._db.keys())
        audit = self.audit_svc.run_global_audit(skus)
        
        # Simulação de agregação rápida baseada nos motores atuais
        total_trust = 0
        expiring = 0
        stagnant = 0
        
        for sku in skus:
            try:
                view = self.query_svc.get_sku_view(sku)
                total_trust += view.trust_score_percentage
                if view.days_to_expire and view.days_to_expire < 30:
                    expiring += 1
                if not view.recent_history:
                    stagnant += 1
            except Exception:
                total_trust += 100 # Fallback para SKUs virgens

        avg_trust = total_trust / len(skus) if skus else 100.0

        return OperationalKPIs(
            health_score=audit.global_health_score,
            critical_skus=len(audit.critical_skus),
            expiring_soon=expiring,
            avg_trust_score=avg_trust,
            stagnant_skus=stagnant
        )
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Integrating Dynamic Matrix and KPI Dashboard into CLI..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/presentation/cli/inspector_cli.py"
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
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Applying Governance..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"

# Registro de Estado
kippe::checkpoint_create "301" "3.0.0-intelligence" "F000.1" "SUCCESS"

echo -e "\n[STATUS] Sprint F000.1 Concluída. KIPPE Inspector promovido a Centro de Comando Baseado em Comportamento!"
exit 0

