from dataclasses import dataclass
from werkzeug.security import generate_password_hash, check_password_hash
from src.domain.result import Result

@dataclass
class Operator:
    id: str
    name: str
    pin_hash: str
    role: str = "OPERADOR"

    def verify_pin(self, pin: str) -> bool:
        """Verifica o PIN em tempo constante contra o hash criptográfico."""
        return check_password_hash(self.pin_hash, str(pin))

    @classmethod
    def create(cls, id: str, name: str, pin: str, role: str = "OPERADOR") -> Result['Operator', str]:
        """Factory method blindada com regras de segurança na criação."""
        if len(str(pin)) < 4 or not str(pin).isdigit():
            return Result.fail("O PIN deve conter no mínimo 4 dígitos numéricos.")
        
        if role not in ["OPERADOR", "GERENTE"]:
            return Result.fail(f"Role de segurança [{role}] inválida.")
        
        # Algoritmo seguro com salt aleatório embutido
        hashed_pin = generate_password_hash(str(pin))
        return Result.ok(cls(id=id, name=name, pin_hash=hashed_pin, role=role))
