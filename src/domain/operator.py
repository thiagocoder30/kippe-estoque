from dataclasses import dataclass

from werkzeug.security import check_password_hash, generate_password_hash

from src.domain.access_control import AccessControl
from src.domain.result import Result


@dataclass
class Operator:
    id: str
    name: str
    pin_hash: str
    role: str = AccessControl.ROLE_OPERATOR

    def verify_pin(self, pin: str) -> bool:
        """Verifica o PIN contra o hash criptográfico armazenado."""
        return check_password_hash(
            self.pin_hash,
            str(pin),
        )

    @classmethod
    def create(
        cls,
        id: str,
        name: str,
        pin: str,
        role: str = AccessControl.ROLE_OPERATOR,
    ) -> Result["Operator", str]:
        """
        Cria um operador humano respeitando as invariantes
        de autenticação e RBAC.
        """
        normalized_id = str(id).strip()
        normalized_name = str(name).strip()
        normalized_pin = str(pin)
        normalized_role = str(role).strip().upper()

        if not normalized_id:
            return Result.fail(
                "O ID do operador é obrigatório."
            )

        if not normalized_name:
            return Result.fail(
                "O nome do operador é obrigatório."
            )

        if (
            len(normalized_pin) < 4
            or not normalized_pin.isdigit()
        ):
            return Result.fail(
                "O PIN deve conter no mínimo 4 dígitos numéricos."
            )

        if not AccessControl.is_valid_human_role(
            normalized_role
        ):
            return Result.fail(
                f"Role de segurança [{normalized_role}] inválida."
            )

        hashed_pin = generate_password_hash(
            normalized_pin
        )

        return Result.ok(
            cls(
                id=normalized_id,
                name=normalized_name,
                pin_hash=hashed_pin,
                role=normalized_role,
            )
        )
