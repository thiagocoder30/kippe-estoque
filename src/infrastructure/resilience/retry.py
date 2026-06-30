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
