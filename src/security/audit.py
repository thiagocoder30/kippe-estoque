import json
import os
from src.security.correlation import ExecutionContext

class AuditLogger:
    """Registrador de Auditoria Estruturado (NDJSON)."""
    def __init__(self, log_dir: str = "data/audit"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, "procurement_audit.log")

    def log_operation(self, context: ExecutionContext, action: str, aggregate_id: str, status: str, details: dict = None):
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
            f.write("\n")
