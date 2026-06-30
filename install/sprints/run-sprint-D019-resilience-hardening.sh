#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D019: RESILIENCE & FAULT TOLERANCE
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
kippe::banner_program "D" "D019" "Resilience & Fault Tolerance"

# Preparação de Diretórios de Resiliência
mkdir -p "${KIPPE_ROOT}/src/infrastructure/resilience"
mkdir -p "${KIPPE_ROOT}/tests/infrastructure/resilience"
touch "${KIPPE_ROOT}/src/infrastructure/resilience/__init__.py"
touch "${KIPPE_ROOT}/tests/infrastructure/resilience/__init__.py"

kippe::step 1 ${TOTAL_STEPS} "Deploying Failure Classification & Exceptions..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/resilience/exceptions.py"
from src.security.exceptions import DomainException

class CircuitBreakerOpenException(DomainException):
    """Lançada quando o disjuntor está aberto e rejeita execuções preventivamente."""
    pass
KIPPE_HUNK

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/resilience/failure_policy.py"
import json
from src.security.exceptions import ValidationException, NotFoundException, BusinessRuleViolation

class FailurePolicy:
    """
    Política Centralizada de Classificação de Falhas.
    Distingue erros transientes (recuperáveis) de falhas permanentes (irrecuperáveis).
    """
    @staticmethod
    def is_transient(exc: Exception) -> bool:
        # Erros de validação, regras de negócio e violações estruturais são permanentes
        if isinstance(exc, (ValidationException, NotFoundException, BusinessRuleViolation)):
            return False
        if isinstance(exc, json.JSONDecodeError):
            return False
            
        # Erros de sistema operacional, permissões temporárias e estouros de tempo são transientes
        if isinstance(exc, (OSError, PermissionError, TimeoutError, ConnectionError)):
            return True
            
        return False
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Retry Engine, Circuit Breaker & Quarantine Components..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/resilience/circuit_breaker.py"
import time
from src.infrastructure.resilience.exceptions import CircuitBreakerOpenException

class CircuitBreaker:
    """
    Disjuntor de Infraestrutura.
    Protege o sistema contra falhas repetitivas em recursos de I/O degradados.
    Estados: CLOSED, OPEN, HALF_OPEN.
    """
    def __init__(self, failure_threshold: int = 3, recovery_timeout_seconds: float = 0.2):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_seconds
        self.failure_count = 0
        self.state = "CLOSED"
        self.last_state_change = time.time()

    def execute(self, func, *args, **kwargs):
        self._evaluate_state()
        
        if self.state == "OPEN":
            raise CircuitBreakerOpenException("Operação rejeitada: Disjuntor aberto devido a falhas consecutivas.")
            
        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self._reset()
            return result
        except Exception as e:
            self._handle_failure()
            raise e

    def _evaluate_state(self):
        if self.state == "OPEN" and (time.time() - self.last_state_change) >= self.recovery_timeout:
            self.state = "HALF_OPEN"
            self.last_state_change = time.time()

    def _handle_failure(self):
        self.failure_count += 1
        if self.state in ["CLOSED", "HALF_OPEN"] and self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.last_state_change = time.time()

    def _reset(self):
        self.failure_count = 0
        self.state = "CLOSED"
        self.last_state_change = time.time()
KIPPE_HUNK

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/resilience/retry.py"
import time
from src.infrastructure.resilience.failure_policy import FailurePolicy

class RetryEngine:
    """
    Mecanismo de Retentativas com Backoff Exponencial.
    Atua exclusivamente sobre falhas classificadas como transientes.
    """
    @staticmethod
    def execute(func, max_attempts: int = 3, base_delay: float = 0.001, *args, **kwargs):
        attempts = 0
        while attempts < max_attempts:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                attempts += 1
                if not FailurePolicy.is_transient(e) or attempts >= max_attempts:
                    raise e
                # Recuo exponencial estruturado
                time.sleep(base_delay * (2 ** (attempts - 1)))
KIPPE_HUNK

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/resilience/quarantine.py"
import os
import shutil
from datetime import datetime

class QuarantineEngine:
    """
    Mecanismo de Isolamento de Arquivos (Quarentena).
    Move payloads estruturalmente corrompidos para preservação de evidências sem travar o runtime.
    """
    @staticmethod
    def isolate(file_path: str, quarantine_dir: str = "data/quarantine") -> str:
        if not os.path.exists(file_path):
            return ""
        os.makedirs(quarantine_dir, exist_ok=True)
        
        base_name = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = os.path.join(quarantine_dir, f"{timestamp}_{base_name}")
        
        try:
            shutil.move(file_path, dest_path)
            return dest_path
        except OSError:
            return ""
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Deploying Comprehensive Test Suite for Resilience Layer..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/infrastructure/resilience/test_resilience_layer.py"
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
KIPPE_HUNK

kippe::step 4 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Platform Regression Suite..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto de Governança
kippe::checkpoint_create "085" "1.4.0-procurement" "D019" "SUCCESS"

kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D019 (Resilience & Fault Tolerance)" \
    "D020 — Final Integration & Verification" \
    "19/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Camada de Resiliência e Tolerância a Falhas (D019) selada operacionalmente."
exit 0

