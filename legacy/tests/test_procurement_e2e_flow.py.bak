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
