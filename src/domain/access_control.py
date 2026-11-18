"""
Política central de controle de acesso do KIPPE WMS.

Roles humanas:
- OPERADOR: execução operacional básica.
- CONFERENTE: conferência física de recebimento (sem alterar catálogo ou saldo direto).
- ESTOQUISTA: gestão de catálogo, cadastro de novos SKUs, armazenagem e efetivação de estoque.
- GERENTE: gestão operacional.
- ADMIN_SISTEMA: administração máxima da aplicação e acesso irrestrito.

Identidade técnica:
- SYSTEM: identidade interna utilizada por processos do sistema.
"""


class AccessControl:
    ROLE_OPERATOR = "OPERADOR"
    ROLE_CONFERENTE = "CONFERENTE"
    ROLE_ESTOQUISTA = "ESTOQUISTA"
    ROLE_MANAGER = "GERENTE"
    ROLE_SYSTEM_ADMIN = "ADMIN_SISTEMA"
    ROLE_SYSTEM = "SYSTEM"

    HUMAN_ROLES = frozenset(
        {
            ROLE_OPERATOR,
            ROLE_CONFERENTE,
            ROLE_ESTOQUISTA,
            ROLE_MANAGER,
            ROLE_SYSTEM_ADMIN,
        }
    )

    CONFERENCE_ONLY_ROLES = frozenset(
        {
            ROLE_OPERATOR,
            ROLE_CONFERENTE,
        }
    )

    MANAGEMENT_ROLES = frozenset(
        {
            ROLE_ESTOQUISTA,
            ROLE_MANAGER,
            ROLE_SYSTEM_ADMIN,
            ROLE_SYSTEM,
        }
    )

    @classmethod
    def is_valid_human_role(cls, role: str) -> bool:
        return str(role or "").strip().upper() in cls.HUMAN_ROLES

    @classmethod
    def is_conference_only(cls, role: str) -> bool:
        return str(role or "").strip().upper() in cls.CONFERENCE_ONLY_ROLES

    @classmethod
    def can_manage_operational_catalog(cls, role: str) -> bool:
        return str(role or "").strip().upper() in cls.MANAGEMENT_ROLES

    @classmethod
    def can_approve_receiving(cls, role: str) -> bool:
        return str(role or "").strip().upper() in cls.MANAGEMENT_ROLES

    @classmethod
    def is_system_admin(cls, role: str) -> bool:
        return str(role or "").strip().upper() == cls.ROLE_SYSTEM_ADMIN
