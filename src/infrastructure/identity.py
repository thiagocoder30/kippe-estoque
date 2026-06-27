from flask import has_request_context, request, session
from src.interfaces.identity import IdentityProvider

class CurrentOperatorResolver(IdentityProvider):
    """
    Adapter que resolve a identidade propagada através das fronteiras do sistema.
    Trata contextos web (Flask session) e contextos isolados de domínio (Testes/CLI).
    """
    def __init__(self, env: str):
        self.env = env
        self.override_id = None # Utilizado estritamente em sandboxes de testes isolados

    def get_current_operator_id(self) -> str:
        if self.override_id: 
            return self.override_id
            
        if has_request_context():
            # Test Security Bridge Injection
            if self.env == "testing" and "X-Test-Operator-Override" in request.headers:
                return request.headers.get("X-Test-Operator-Override")
            # Production AuthN Session
            return session.get('operator_id', 'SYSTEM')
            
        # Fallback de segurança para execuções assíncronas/CRON futuras
        return 'SYSTEM'
