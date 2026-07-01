import os
from src.infrastructure.monitoring.telemetry import TelemetryEngine, AuditTrail, MetricsRegistry

def test_telemetry_engine_captures_metrics_and_evaluates_health(tmp_path):
    event_store_mock = tmp_path / "events.jsonl"
    # Popula 2 eventos simulados no arquivo
    with open(event_store_mock, "w") as f:
        f.write("{}\n{}\n")
        
    snapshot = TelemetryEngine.capture(event_store_path=str(event_store_mock), simulated_failures=0)
    
    assert snapshot.health_status == "HEALTHY"
    assert snapshot.metrics[MetricsRegistry.COMMANDS_RECEIVED] == 2
    assert snapshot.metrics[MetricsRegistry.EVENTSTORE_SIZE] > 0

def test_health_monitor_triggers_degraded_state(tmp_path):
    event_store_mock = tmp_path / "events.jsonl"
    event_store_mock.touch()
    
    # Simula falhas pontuais no processamento
    snapshot = TelemetryEngine.capture(event_store_path=str(event_store_mock), simulated_failures=3)
    assert snapshot.health_status == "WARNING"

def test_audit_trail_writes_infrastructure_logs(tmp_path):
    audit_file = tmp_path / "audit_trail.jsonl"
    trail = AuditTrail(file_path=str(audit_file))
    
    trail.log_infra_event("System Initialized", {"version": "1.5.0"})
    
    assert os.path.exists(audit_file)
    with open(audit_file, "r") as f:
        line = f.readline()
        assert "System Initialized" in line
        assert "1.5.0" in line
