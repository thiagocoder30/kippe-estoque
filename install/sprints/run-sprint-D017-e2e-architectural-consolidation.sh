#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D017: E2E TESTING & ARCHITECTURAL CONSOLIDATION
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

# 1. Carregamento do Framework
source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

# Blindagem de Infraestrutura (Fail-Fast)
for fn in kippe::init kippe::validate_script_syntax kippe::test_execute_all kippe::checkpoint_create; do
    if ! declare -F "$fn" >/dev/null; then
        echo "[FATAL] Framework function missing: $fn. O script foi interrompido."
        exit 1
    fi
done

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=4
kippe::banner_program "D" "D017" "E2E Testing & Architectural Consolidation"

# Preparação de Diretórios
mkdir -p "${KIPPE_ROOT}/src/application/ports"
mkdir -p "${KIPPE_ROOT}/src/infrastructure/observability"
mkdir -p "${KIPPE_ROOT}/tests/e2e"
touch "${KIPPE_ROOT}/src/application/ports/__init__.py"
touch "${KIPPE_ROOT}/src/infrastructure/observability/__init__.py"
touch "${KIPPE_ROOT}/tests/e2e/__init__.py"

kippe::step 1 ${TOTAL_STEPS} "Deploying Application Ports (Interfaces) for Observability & Security..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/application/ports/observability.py"
from abc import ABC, abstractmethod
from typing import Dict, Any
from src.security.correlation import ExecutionContext

class AuditPort(ABC):
    """Porta (Interface) para Auditoria. O Application Layer não conhece a implementação."""
    @abstractmethod
    def log_operation(self, context: ExecutionContext, action: str, aggregate_id: str, status: str, details: Dict[str, Any] = None) -> None:
        pass

class MetricsPort(ABC):
    """Porta para coleta de métricas de negócio (ex: Prometheus, Datadog)."""
    @abstractmethod
    def increment_counter(self, metric_name: str, tags: Dict[str, str] = None) -> None:
        pass
KIPPE_HUNK

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/application/ports/security.py"
from abc import ABC, abstractmethod
from src.security.correlation import ExecutionContext

class AuthorizationPort(ABC):
    """Porta para o Serviço de Autorização."""
    @abstractmethod
    def can_execute(self, context: ExecutionContext, action: str) -> bool:
        pass
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Infrastructure Implementations & Cross-Cutting Decorators..."

# Implementação concreta da Auditoria na Infraestrutura (onde pertence)
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/observability/ndjson_audit.py"
import os
import json
from typing import Dict, Any
from src.application.ports.observability import AuditPort
from src.security.correlation import ExecutionContext

class NDJSONAuditLogger(AuditPort):
    def __init__(self, log_dir: str = "data/audit"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, "procurement_audit.log")

    def log_operation(self, context: ExecutionContext, action: str, aggregate_id: str, status: str, details: Dict[str, Any] = None) -> None:
        log_entry = {
            "timestamp": context.timestamp,
            "correlation_id": context.correlation_id,
            "user": context.user_id,
            "action": action,
            "aggregate_id": aggregate_id,
            "status": status,
            "details": details or {}
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            json.dump(log_entry, f, ensure_ascii=False)
            f.write("\n") # Correção: Injeta quebra de linha real no arquivo Python final (NDJSON estável)
KIPPE_HUNK

# Decorator para envolver os Use Cases sem poluir o Domínio
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/application/middleware/decorators.py"
from typing import Any
from src.security.correlation import ExecutionContext
from src.application.ports.observability import AuditPort
from src.security.exceptions import AuthorizationException
from src.application.ports.security import AuthorizationPort

class UseCaseAuditDecorator:
    """Decorator Transversal: Intercepta a execução para gravar auditoria sem alterar o Use Case."""
    def __init__(self, use_case: Any, action_name: str, audit_port: AuditPort, auth_port: AuthorizationPort = None):
        self._use_case = use_case
        self._action_name = action_name
        self._audit = audit_port
        self._auth = auth_port

    def execute(self, context: ExecutionContext, *args, **kwargs) -> Any:
        # 1. Autorização (Se existir porta)
        if self._auth and not self._auth.can_execute(context, self._action_name):
            self._audit.log_operation(context, self._action_name, "N/A", "FORBIDDEN")
            raise AuthorizationException(f"Usuário {context.user_id} não autorizado para {self._action_name}.")

        # 2. Execução Pura do Use Case
        try:
            result = self._use_case.execute(context, *args, **kwargs)
            
            # Tenta extrair ID do agregado retornado para o log, ou fallback
            agg_id = getattr(result, 'id', kwargs.get('order_id', args[0] if args else "UNKNOWN"))
            self._audit.log_operation(context, self._action_name, agg_id, "SUCCESS")
            return result
        except Exception as e:
            agg_id_err = kwargs.get('order_id', args[0] if args else "UNKNOWN")
            self._audit.log_operation(context, self._action_name, agg_id_err, "FAILED", {"reason": str(e)})
            raise
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Refactoring Use Cases to Pure Form & Updating Composition Root..."

# O Use Case volta a ser Puro, sem conhecimento de Audit ou Decorators
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/application/procurement/use_cases.py"
from typing import Dict, Any
from src.domain.procurement.order import PurchaseOrder
from src.domain.procurement.repository import PurchaseOrderRepository
from src.domain.procurement.supplier_repository import SupplierRepository
from src.security.correlation import ExecutionContext
from src.security.exceptions import NotFoundException, BusinessRuleViolation
from src.application.procurement.validators import CreatePurchaseOrderValidator

class CreatePurchaseOrderUseCase:
    """Use Case Purificado. Sem referências a infraestrutura transversal."""
    def __init__(self, po_repo: PurchaseOrderRepository, sup_repo: SupplierRepository):
        self.po_repo = po_repo
        self.sup_repo = sup_repo

    def execute(self, context: ExecutionContext, order_id: str, supplier_id: str, items: list[Dict[str, Any]]) -> PurchaseOrder:
        CreatePurchaseOrderValidator.validate(order_id, supplier_id, items)

        supplier = self.sup_repo.get_by_id(supplier_id)
        if not supplier:
            raise NotFoundException(f"Fornecedor {supplier_id} não encontrado.")
        if supplier.status != "ACTIVE":
            raise BusinessRuleViolation(f"Fornecedor {supplier_id} não está ativo para novas compras.")

        order = PurchaseOrder(id=order_id, supplier_id=supplier_id)
        for item in items:
            order.add_item(
                sku=item["sku"], quantity=item["quantity"],
                unit_price=item["unit_price"], discount=item.get("discount", 0.0), tax=item.get("tax", 0.0)
            )

        self.po_repo.save(order)
        return order

class ApprovePurchaseOrderUseCase:
    def __init__(self, po_repo: PurchaseOrderRepository):
        self.po_repo = po_repo

    def execute(self, context: ExecutionContext, order_id: str) -> None:
        order = self.po_repo.get_by_id(order_id)
        if not order:
            raise NotFoundException(f"Pedido {order_id} não encontrado.")

        try:
            order.approve()
            self.po_repo.save(order)
        except ValueError as e:
            raise BusinessRuleViolation(str(e))
KIPPE_HUNK

# Bootstrap agora orquestra os Middlewares/Decorators em volta dos UseCases
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/bootstrap.py"
from src.infrastructure.persistence.json.purchase_order_repository import JsonPurchaseOrderRepository
from src.infrastructure.persistence.json.supplier_repository import JsonSupplierRepository
from src.infrastructure.observability.ndjson_audit import NDJSONAuditLogger
from src.application.procurement.use_cases import CreatePurchaseOrderUseCase, ApprovePurchaseOrderUseCase
from src.application.middleware.decorators import UseCaseAuditDecorator

class Bootstrap:
    """
    Composition Root Consolidado.
    Monta os Repositórios, os Use Cases Puros e injeta os Decorators Transversais.
    """
    def __init__(self, use_memory: bool = False):
        if use_memory:
            from src.infrastructure.persistence.in_memory.purchase_order_repository import InMemoryPurchaseOrderRepository
            from src.infrastructure.persistence.in_memory.supplier_repository import InMemorySupplierRepository
            self.po_repo = InMemoryPurchaseOrderRepository()
            self.sup_repo = InMemorySupplierRepository()
        else:
            self.po_repo = JsonPurchaseOrderRepository()
            self.sup_repo = JsonSupplierRepository()

        # Portas Transversais (Infra)
        self.audit_port = NDJSONAuditLogger()

        # Instanciação Pura (Core)
        base_create_uc = CreatePurchaseOrderUseCase(self.po_repo, self.sup_repo)
        base_approve_uc = ApprovePurchaseOrderUseCase(self.po_repo)

        # Envolvimento Transversal (Decorators)
        self.create_po_uc = UseCaseAuditDecorator(base_create_uc, "CREATE_PO", self.audit_port)
        self.approve_po_uc = UseCaseAuditDecorator(base_approve_uc, "APPROVE_PO", self.audit_port)

    def get_create_po_use_case(self):
        return self.create_po_uc

    def get_approve_po_use_case(self):
        return self.approve_po_uc
KIPPE_HUNK

kippe::step 4 ${TOTAL_STEPS} "Deploying End-to-End Architectural Test..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/e2e/test_procurement_e2e_flow.py"
import os
import json
import pytest
from src.bootstrap import Bootstrap
from src.domain.procurement.supplier import Supplier
from src.security.correlation import ExecutionContext

def test_full_architectural_consolidation_flow(tmp_path):
    """
    E2E Test: Presentation -> Middleware -> Application -> Domain -> Infrastructure
    Valida se o Decorator grava a auditoria de forma estável no padrão NDJSON.
    """
    app = Bootstrap(use_memory=True)
    app.audit_port.log_file = str(tmp_path / "test_audit.log")
    
    # Prepara Domínio
    app.sup_repo.save(Supplier("SUP-E2E", "Corp", "001", "a@a.com", "ACTIVE"))
    
    # 1. Simula requisição da Presentation Layer
    ctx = ExecutionContext(user_id="U-FRONTEND")
    create_uc = app.get_create_po_use_case()
    
    # 2. Executa caso de uso (atravessa Decorator -> Validator -> UseCase -> Domain -> Repo)
    order = create_uc.execute(ctx, "PO-E2E-01", "SUP-E2E", [{"sku": "ITM-1", "quantity": 10, "unit_price": 50.0}])
    
    assert order.id == "PO-E2E-01"
    assert order.status == "DRAFT"
    
    # 3. Validação do Middleware (Audit) - Lendo linhas individuais sem quebra por escape
    assert os.path.exists(app.audit_port.log_file)
    with open(app.audit_port.log_file, "r", encoding="utf-8") as f:
        log_lines = f.readlines()
        
    assert len(log_lines) == 1
    log_data = json.loads(log_lines[0].strip())
    
    assert log_data["action"] == "CREATE_PO"
    assert log_data["status"] == "SUCCESS"
    assert log_data["correlation_id"] == ctx.correlation_id
    assert log_data["aggregate_id"] == "PO-E2E-01"
KIPPE_HUNK

kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "081" "1.4.0-procurement" "D017" "SUCCESS"

kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D017 (Architectural Consolidation & E2E)" \
    "D018 — Database Migrations & Versioning" \
    "17/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Consolidação Arquitetural e Testes E2E (D017) implantados com sucesso."
exit 0

