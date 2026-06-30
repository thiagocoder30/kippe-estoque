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
