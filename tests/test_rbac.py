import os

import pytest

from src.infrastructure.config import Config
from src.infrastructure.container import Container


@pytest.fixture
def rbac_ctx():
    cfg = Config.for_testing()
    c = Container(cfg)

    c.product_repository._init_db()

    with c.product_repository._get_connection() as conn:
        conn.execute("DELETE FROM products")
        conn.commit()

    yield c

    if os.path.exists(cfg.DB_PATH):
        os.remove(cfg.DB_PATH)


def test_rbac_manager_can_create_product(rbac_ctx):
    rbac_ctx.identity_provider.override_id = "MGR-01"
    rbac_ctx.identity_provider.override_role = "GERENTE"

    res = rbac_ctx.use_case.create_product(
        "NEW-1",
        "Produto Teste",
    )

    assert res.is_success is True


def test_rbac_admin_sistema_can_create_product(rbac_ctx):
    rbac_ctx.identity_provider.override_id = "ADM-01"
    rbac_ctx.identity_provider.override_role = "ADMIN_SISTEMA"

    res = rbac_ctx.use_case.create_product(
        "NEW-ADMIN-1",
        "Produto Administrador",
    )

    assert res.is_success is True


def test_rbac_operator_cannot_create_product(rbac_ctx):
    rbac_ctx.identity_provider.override_id = "OP-01"
    rbac_ctx.identity_provider.override_role = "OPERADOR"

    res = rbac_ctx.use_case.create_product(
        "NEW-2",
        "Produto Ilegal",
    )

    assert res.is_success is False
    assert "Autorização negada" in res.error


def test_rbac_admin_sistema_can_create_category(rbac_ctx):
    rbac_ctx.identity_provider.override_id = "ADM-01"
    rbac_ctx.identity_provider.override_role = "ADMIN_SISTEMA"

    res = rbac_ctx.category_use_case.create_category(
        "CAT-ADMIN-1",
        "Categoria Administrador",
        None,
    )

    assert res.is_success is True


def test_rbac_operator_cannot_create_category(rbac_ctx):
    rbac_ctx.identity_provider.override_id = "OP-01"
    rbac_ctx.identity_provider.override_role = "OPERADOR"

    res = rbac_ctx.category_use_case.create_category(
        "CAT-OP-1",
        "Categoria Não Permitida",
        None,
    )

    assert res.is_success is False
    assert "Autorização negada" in res.error
