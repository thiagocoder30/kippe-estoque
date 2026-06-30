import pytest
import json
import os
from src.infrastructure.resilience.failure_policy import FailurePolicy
from src.infrastructure.resilience.retry import RetryEngine
from src.infrastructure.resilience.circuit_breaker import CircuitBreaker
from src.infrastructure.resilience.quarantine import QuarantineEngine
from src.infrastructure.resilience.exceptions import CircuitBreakerOpenException
from src.security.exceptions import ValidationException

def test_failure_classification_policy():
    assert FailurePolicy.is_transient(OSError("Disco ocupado")) is True
    assert FailurePolicy.is_transient(TimeoutError("Timeout de escrita")) is True
    assert FailurePolicy.is_transient(ValidationException("Invariante violada")) is False
    assert FailurePolicy.is_transient(json.JSONDecodeError("Erro sintaxe", "", 0)) is False

def test_retry_engine_backs_off_on_transient_errors():
    call_count = 0
    def failing_transient_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise OSError("Falha temporária")
        return "SUCCESS"

    result = RetryEngine.execute(failing_transient_function, max_attempts=3, base_delay=0.001)
    assert result == "SUCCESS"
    assert call_count == 3

def test_retry_engine_stops_immediately_on_permanent_errors():
    call_count = 0
    def failing_permanent_function():
        nonlocal call_count
        call_count += 1
        raise ValidationException("Erro permanente")

    with pytest.raises(ValidationException):
        RetryEngine.execute(failing_permanent_function, max_attempts=3)
    assert call_count == 1

def test_circuit_breaker_transitions():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=0.05)
    
    def dummy_fail():
        raise OSError("Falha física")
        
    # Força abertura do disjuntor
    with pytest.raises(OSError): cb.execute(dummy_fail)
    with pytest.raises(OSError): cb.execute(dummy_fail)
    
    assert cb.state == "OPEN"
    
    # Rejeição imediata por proteção sem executar a função de destino
    with pytest.raises(CircuitBreakerOpenException):
        cb.execute(lambda: "Não deve rodar")

def test_quarantine_isolates_corrupted_payload(tmp_path):
    bad_file = tmp_path / "corrupted_orders.json"
    bad_file.write_text("{malformed json...", encoding="utf-8")
    
    q_dir = str(tmp_path / "quarantine_box")
    dest = QuarantineEngine.isolate(str(bad_file), quarantine_dir=q_dir)
    
    assert os.path.exists(dest)
    assert not os.path.exists(str(bad_file))
