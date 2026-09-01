import os

import pytest

from src.infrastructure.config import Config
from src.infrastructure.container import Container


@pytest.fixture
def product_registration_context():
    config = Config.for_testing()
    container = Container(config)

    container.product_repository._init_db()

    container.identity_provider.override_id = (
        "PRODUCT-REGISTRATION-TEST"
    )
    container.identity_provider.override_role = (
        "GERENTE"
    )

    yield container, config

    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)

    if os.path.exists(config.LOG_PATH):
        os.remove(config.LOG_PATH)


def test_operational_registration_generates_sku_automatically(
    product_registration_context,
):
    container, _ = product_registration_context

    result = container.use_case.register_product(
        name="Mistura Para Bolo Vilma Coco 400g Pct",
        ean="7896417209999",
        unit_of_measure="un",
        category_id=None,
    )

    assert result.is_success is True

    created = result.value

    assert created["id"] == "SKU000001"
    assert created["ean"] == "7896417209999"
    assert (
        created["name"]
        == "Mistura Para Bolo Vilma Coco 400g Pct"
    )


def test_automatic_sku_sequence_is_monotonic(
    product_registration_context,
):
    container, _ = product_registration_context

    first = container.use_case.register_product(
        name="Produto Um",
        ean="7890000000001",
        unit_of_measure="un",
        category_id=None,
    )

    second = container.use_case.register_product(
        name="Produto Dois",
        ean="7890000000002",
        unit_of_measure="un",
        category_id=None,
    )

    assert first.is_success is True
    assert second.is_success is True

    assert first.value["id"] == "SKU000001"
    assert second.value["id"] == "SKU000002"


def test_operational_registration_rejects_duplicate_ean(
    product_registration_context,
):
    container, _ = product_registration_context

    first = container.use_case.register_product(
        name="Produto Original",
        ean="7890000000018",
        unit_of_measure="un",
        category_id=None,
    )

    duplicate = container.use_case.register_product(
        name="Produto Duplicado",
        ean="7890000000018",
        unit_of_measure="un",
        category_id=None,
    )

    assert first.is_success is True
    assert duplicate.is_success is False

    assert "EAN" in duplicate.error
    assert "já" in duplicate.error.lower()


def test_duplicate_ean_does_not_consume_next_sku(
    product_registration_context,
):
    container, _ = product_registration_context

    first = container.use_case.register_product(
        name="Produto Original",
        ean="7890000000025",
        unit_of_measure="un",
        category_id=None,
    )

    duplicate = container.use_case.register_product(
        name="Produto Repetido",
        ean="7890000000025",
        unit_of_measure="un",
        category_id=None,
    )

    second_valid = container.use_case.register_product(
        name="Produto Seguinte",
        ean="7890000000032",
        unit_of_measure="un",
        category_id=None,
    )

    assert first.is_success is True
    assert duplicate.is_success is False
    assert second_valid.is_success is True

    assert first.value["id"] == "SKU000001"
    assert second_valid.value["id"] == "SKU000002"


def test_generated_sku_product_is_persisted_and_queryable_by_ean(
    product_registration_context,
):
    container, _ = product_registration_context

    result = container.use_case.register_product(
        name="Leite Integral Teste",
        ean="7890000000049",
        unit_of_measure="un",
        category_id=None,
    )

    assert result.is_success is True

    generated_sku = result.value["id"]

    by_sku = (
        container.product_repository.get_by_id(
            generated_sku
        )
    )

    assert by_sku is not None
    assert by_sku.id == generated_sku
    assert by_sku.ean == "7890000000049"

    query = (
        container.product_query_use_case.execute(
            "7890000000049"
        )
    )

    assert query.is_success is True
    assert query.value["id"] == generated_sku
    assert query.value["ean"] == "7890000000049"
