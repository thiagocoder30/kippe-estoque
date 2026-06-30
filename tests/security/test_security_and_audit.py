import os
import json
import pytest
from src.security.correlation import ExecutionContext
from src.security.audit import AuditLogger
from src.security.exceptions import ValidationException
from src.application.procurement.validators import CreatePurchaseOrderValidator

def test_execution_context_generates_correlation_id():
    ctx = ExecutionContext(user_id="U123")
    assert ctx.user_id == "U123"
    assert ctx.correlation_id.startswith("CTX-")
    assert "[CTX:" in ctx.to_log_format()

def test_audit_logger_writes_structured_json(tmp_path):
    log_dir = str(tmp_path / "audit_logs")
    logger = AuditLogger(log_dir=log_dir)
    ctx = ExecutionContext()
    
    logger.log_operation(ctx, "TEST_ACTION", "AGG-1", "SUCCESS", {"meta": "data"})
    
    log_file = os.path.join(log_dir, "procurement_audit.log")
    assert os.path.exists(log_file)
    
    with open(log_file, "r", encoding="utf-8") as f:
        log_entry = json.loads(f.readline())
        assert log_entry["correlation_id"] == ctx.correlation_id
        assert log_entry["action"] == "TEST_ACTION"
        assert log_entry["status"] == "SUCCESS"

def test_create_po_validator_catches_invalid_inputs():
    with pytest.raises(ValidationException, match="order_id inválido"):
        CreatePurchaseOrderValidator.validate("", "SUP-1", [{"sku": "A", "quantity": 1, "unit_price": 1.0}])
        
    with pytest.raises(ValidationException, match="lista de itens não pode estar vazia"):
        CreatePurchaseOrderValidator.validate("PO-1", "SUP-1", [])
        
    with pytest.raises(ValidationException, match="Quantidade inválida"):
        CreatePurchaseOrderValidator.validate("PO-1", "SUP-1", [{"sku": "A", "quantity": -5, "unit_price": 1.0}])
