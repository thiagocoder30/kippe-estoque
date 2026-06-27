from flask import has_request_context, request, session
from src.interfaces.identity import IdentityProvider

class CurrentOperatorResolver(IdentityProvider):
    def __init__(self, env: str):
        self.env = env
        self.override_id = None 
        self.override_role = None # Injeção de cargo para testes isolados

    def get_current_operator_id(self) -> str:
        if self.override_id: return self.override_id
        if has_request_context():
            if self.env == "testing" and "X-Test-Operator-Override" in request.headers:
                return request.headers.get("X-Test-Operator-Override")
            return session.get('operator_id', 'SYSTEM')
        return 'SYSTEM'

    def get_current_operator_role(self) -> str:
        if self.override_role: return self.override_role
        if has_request_context():
            if self.env == "testing" and "X-Test-Role-Override" in request.headers:
                return request.headers.get("X-Test-Role-Override")
            return session.get('operator_role', 'SYSTEM')
        return 'SYSTEM'
