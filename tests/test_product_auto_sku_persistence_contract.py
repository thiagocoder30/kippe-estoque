import os
import sqlite3

import pytest

from src.infrastructure.config import Config
from src.infrastructure.container import Container


@pytest.fixture
def auto_sku_context():
    config = Config.for_testing()
    container = Container(config)

    container.product_repository._init_db()

    container.identity_provider.override_id = (
        "AUTO-SKU-PERSISTENCE-TEST"
    )
    container.identity_provider.override_role = (
        "GERENTE"
    )

    yield container, config

    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)

    if os.path.exists(config.LOG_PATH):
        os.remove(config.LOG_PATH)


def test_operator_cannot_use_automatic_product_registration(
    auto_sku_context,
):
    container, _ = auto_sku_context

    container.identity_provider.override_role = (
        "OPERADOR"
    )

    result = container.use_case.register_product(
        name="Produto Bloqueado",
        ean="7890000000100",
        unit_of_measure="un",
        category_id=None,
    )

    assert result.is_success is False
    assert "Autorização negada" in result.error


def test_historical_noncanonical_sku_does_not_shift_sequence(
    auto_sku_context,
):
    container, _ = auto_sku_context

    legacy = container.use_case.create_product(
        product_id="SKU001",
        name="Produto Histórico",
        ean="7890000000117",
        unit_of_measure="un",
    )

    assert legacy.is_success is True

    generated = container.use_case.register_product(
        name="Produto Automático",
        ean="7890000000124",
        unit_of_measure="un",
        category_id=None,
    )

    assert generated.is_success is True
    assert generated.value["id"] == "SKU000001"


def test_existing_canonical_sku_initializes_sequence_after_highest(
    auto_sku_context,
):
    container, config = auto_sku_context

    container.use_case.create_product(
        product_id="SKU000007",
        name="Produto Sete",
        ean="7890000000131",
        unit_of_measure="un",
    )

    with sqlite3.connect(config.DB_PATH) as conn:
        conn.execute(
            """
            DELETE FROM sku_sequences
            WHERE name = 'product'
            """
        )
        conn.commit()

    container.product_repository._init_db()

    generated = container.use_case.register_product(
        name="Produto Oito",
        ean="7890000000148",
        unit_of_measure="un",
        category_id=None,
    )

    assert generated.is_success is True
    assert generated.value["id"] == "SKU000008"


def test_sequence_survives_container_restart(
    auto_sku_context,
):
    container, config = auto_sku_context

    first = container.use_case.register_product(
        name="Produto Primeiro",
        ean="7890000000155",
        unit_of_measure="un",
        category_id=None,
    )

    assert first.is_success is True
    assert first.value["id"] == "SKU000001"

    restarted = Container(config)

    restarted.identity_provider.override_id = (
        "AUTO-SKU-RESTART-TEST"
    )
    restarted.identity_provider.override_role = (
        "GERENTE"
    )

    second = restarted.use_case.register_product(
        name="Produto Segundo",
        ean="7890000000162",
        unit_of_measure="un",
        category_id=None,
    )

    assert second.is_success is True
    assert second.value["id"] == "SKU000002"


def test_duplicate_ean_does_not_consume_sequence_after_restart(
    auto_sku_context,
):
    container, config = auto_sku_context

    first = container.use_case.register_product(
        name="Produto Original",
        ean="7890000000179",
        unit_of_measure="un",
        category_id=None,
    )

    assert first.is_success is True
    assert first.value["id"] == "SKU000001"

    restarted = Container(config)

    restarted.identity_provider.override_id = (
        "AUTO-SKU-DUPLICATE-TEST"
    )
    restarted.identity_provider.override_role = (
        "GERENTE"
    )

    duplicate = restarted.use_case.register_product(
        name="Produto Duplicado",
        ean="7890000000179",
        unit_of_measure="un",
        category_id=None,
    )

    assert duplicate.is_success is False

    valid = restarted.use_case.register_product(
        name="Produto Seguinte",
        ean="7890000000186",
        unit_of_measure="un",
        category_id=None,
    )

    assert valid.is_success is True
    assert valid.value["id"] == "SKU000002"
