import os

import pytest

from src.infrastructure.config import Config
from src.infrastructure.container import Container


@pytest.fixture
def container():
    cfg = Config.for_testing()
    c = Container(cfg)

    # Garante banco limpo para o escopo de teste de segurança.
    c.operator_repository._init_db()

    with c.operator_repository._get_connection() as conn:
        conn.execute("DELETE FROM operators")
        conn.commit()

    yield c

    if os.path.exists(cfg.DB_PATH):
        os.remove(cfg.DB_PATH)

    if os.path.exists(cfg.LOG_PATH):
        os.remove(cfg.LOG_PATH)


def test_operator_pin_is_hashed_and_verified(container):
    auth_uc = container.auth_use_case

    res_reg = auth_uc.register(
        "1045",
        "João Silva",
        "1234",
        "OPERADOR",
    )

    assert res_reg.is_success is True

    operator_raw = container.operator_repository.get_by_id(
        "1045"
    )

    assert operator_raw.pin_hash != "1234"
    assert len(operator_raw.pin_hash) > 20

    res_auth = auth_uc.authenticate(
        "1045",
        "1234",
    )

    assert res_auth.is_success is True
    assert res_auth.value.name == "João Silva"

    res_fail = auth_uc.authenticate(
        "1045",
        "0000",
    )

    assert res_fail.is_success is False
    assert "Credenciais inválidas" in res_fail.error


def test_operator_creation_validation(container):
    auth_uc = container.auth_use_case

    res = auth_uc.register(
        "999",
        "Admin",
        "12",
    )

    assert res.is_success is False

    res2 = auth_uc.register(
        "888",
        "Hacker",
        "1234",
        "SUPERUSER",
    )

    assert res2.is_success is False


def test_admin_sistema_is_valid_security_role(container):
    auth_uc = container.auth_use_case

    res = auth_uc.register(
        "1001",
        "Administrador Teste",
        "4664",
        "ADMIN_SISTEMA",
    )

    assert res.is_success is True

    operator = container.operator_repository.get_by_id(
        "1001"
    )

    assert operator is not None
    assert operator.id == "1001"
    assert operator.name == "Administrador Teste"
    assert operator.role == "ADMIN_SISTEMA"


def test_admin_sistema_can_authenticate(container):
    auth_uc = container.auth_use_case

    registration = auth_uc.register(
        "1001",
        "Administrador Teste",
        "4664",
        "ADMIN_SISTEMA",
    )

    assert registration.is_success is True

    authentication = auth_uc.authenticate(
        "1001",
        "4664",
    )

    assert authentication.is_success is True
    assert authentication.value.role == "ADMIN_SISTEMA"


def test_unknown_security_role_remains_rejected(container):
    auth_uc = container.auth_use_case

    result = auth_uc.register(
        "9999",
        "Usuário Inválido",
        "1234",
        "ROOT",
    )

    assert result.is_success is False
    assert "Role de segurança" in result.error
