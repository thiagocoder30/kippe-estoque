"""
Política central de controle de acesso do KIPPE WMS.

Roles humanas:
- OPERADOR: execução operacional.
- GERENTE: gestão operacional.
- ADMIN_SISTEMA: administração máxima da aplicação e herança
  das capacidades gerenciais.

Identidade técnica:
- SYSTEM: identidade interna utilizada por processos do sistema.
  Não representa um usuário humano cadastrável.
"""


class AccessControl:
    ROLE_OPERATOR = "OPERADOR"
    ROLE_MANAGER = "GERENTE"
    ROLE_SYSTEM_ADMIN = "ADMIN_SISTEMA"
    ROLE_SYSTEM = "SYSTEM"

    HUMAN_ROLES = frozenset(
        {
            ROLE_OPERATOR,
            ROLE_MANAGER,
            ROLE_SYSTEM_ADMIN,
        }
    )

    MANAGEMENT_ROLES = frozenset(
        {
            ROLE_MANAGER,
            ROLE_SYSTEM_ADMIN,
            ROLE_SYSTEM,
        }
    )

    @classmethod
    def is_valid_human_role(cls, role: str) -> bool:
        return role in cls.HUMAN_ROLES

    @classmethod
    def can_manage_operational_catalog(cls, role: str) -> bool:
        return role in cls.MANAGEMENT_ROLES

    @classmethod
    def is_system_admin(cls, role: str) -> bool:
        return role == cls.ROLE_SYSTEM_ADMIN
