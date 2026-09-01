import os

import pytest

from src.domain.category import Category
from src.infrastructure.config import Config
from src.infrastructure.container import Container


EXPECTED_DEFAULT_CATEGORIES = [
    ("MER", "Mercearia", 10),
    ("BEB", "Bebidas", 20),
    ("LAT", "Laticínios e Refrigerados", 30),
    ("CAR", "Carnes e Açougue", 40),
    ("FRI", "Frios e Embutidos", 50),
    ("HOR", "Hortifruti", 60),
    ("PAD", "Padaria e Confeitaria", 70),
    ("CON", "Congelados", 80),
    ("HIG", "Higiene Pessoal", 90),
    ("LIM", "Limpeza", 100),
    ("BAZ", "Bazar e Utilidades", 110),
    ("PET", "Pet", 120),
    ("INF", "Infantil", 130),
    ("COS", "Perfumaria e Cosméticos", 140),
    ("DES", "Descartáveis e Embalagens", 150),
    ("OUT", "Outros", 160),
]


@pytest.fixture
def category_seed_context():
    config = Config.for_testing()
    container = Container(config)

    repository = container.product_repository

    with repository._get_connection() as conn:
        conn.execute(
            "DELETE FROM products"
        )
        conn.execute(
            "DELETE FROM categories"
        )
        conn.commit()

    yield container, config

    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)

    if os.path.exists(config.LOG_PATH):
        os.remove(config.LOG_PATH)


def test_default_category_catalog_contains_expected_supermarket_categories(
    category_seed_context,
):
    container, _ = category_seed_context

    container.product_repository.ensure_default_categories()

    categories = (
        container.product_repository.get_all_categories()
    )

    actual = [
        (
            category.id,
            category.name,
            category.sort_order,
        )
        for category in categories
    ]

    assert actual == EXPECTED_DEFAULT_CATEGORIES


def test_default_categories_are_active_roots(
    category_seed_context,
):
    container, _ = category_seed_context

    container.product_repository.ensure_default_categories()

    categories = (
        container.product_repository.get_all_categories()
    )

    assert len(categories) == len(
        EXPECTED_DEFAULT_CATEGORIES
    )

    for category in categories:
        assert category.active is True
        assert category.parent_id is None


def test_default_category_seed_is_idempotent(
    category_seed_context,
):
    container, _ = category_seed_context

    repository = container.product_repository

    repository.ensure_default_categories()
    repository.ensure_default_categories()
    repository.ensure_default_categories()

    categories = repository.get_all_categories()

    assert len(categories) == len(
        EXPECTED_DEFAULT_CATEGORIES
    )

    assert len(
        {
            category.id
            for category in categories
        }
    ) == len(EXPECTED_DEFAULT_CATEGORIES)


def test_seed_never_overwrites_existing_category(
    category_seed_context,
):
    container, _ = category_seed_context

    repository = container.product_repository

    repository.save_category(
        Category(
            id="MER",
            name="Mercearia Personalizada",
            description="Configuração operacional local.",
            sort_order=999,
            classification_rules={
                "custom": True,
            },
        )
    )

    repository.ensure_default_categories()

    category = repository.get_category_by_id(
        "MER"
    )

    assert category is not None
    assert category.name == (
        "Mercearia Personalizada"
    )
    assert category.description == (
        "Configuração operacional local."
    )
    assert category.sort_order == 999
    assert category.classification_rules == {
        "custom": True,
    }


def test_seed_preserves_existing_inactive_category(
    category_seed_context,
):
    container, _ = category_seed_context

    repository = container.product_repository

    repository.save_category(
        Category(
            id="BEB",
            name="Bebidas",
            active=False,
            sort_order=20,
        )
    )

    repository.ensure_default_categories()

    category = repository.get_category_by_id(
        "BEB"
    )

    assert category is not None
    assert category.active is False


def test_seed_adds_only_missing_categories(
    category_seed_context,
):
    container, _ = category_seed_context

    repository = container.product_repository

    repository.save_category(
        Category(
            id="MER",
            name="Mercearia Existente",
            sort_order=777,
        )
    )

    repository.save_category(
        Category(
            id="CUSTOM",
            name="Categoria Local",
            sort_order=888,
        )
    )

    repository.ensure_default_categories()

    categories = repository.get_all_categories()

    by_id = {
        category.id: category
        for category in categories
    }

    assert (
        len(categories)
        == len(EXPECTED_DEFAULT_CATEGORIES) + 1
    )

    assert by_id["MER"].name == (
        "Mercearia Existente"
    )

    assert by_id["MER"].sort_order == 777

    assert by_id["CUSTOM"].name == (
        "Categoria Local"
    )

    for category_id, name, _ in (
        EXPECTED_DEFAULT_CATEGORIES
    ):
        assert category_id in by_id

        if category_id != "MER":
            assert by_id[category_id].name == name


def test_default_categories_survive_repository_restart(
    category_seed_context,
):
    container, config = category_seed_context

    container.product_repository.ensure_default_categories()

    restarted = Container(config)

    categories = (
        restarted.product_repository.get_all_categories()
    )

    actual_ids = {
        category.id
        for category in categories
    }

    expected_ids = {
        category_id
        for category_id, _, _
        in EXPECTED_DEFAULT_CATEGORIES
    }

    assert expected_ids.issubset(
        actual_ids
    )


def test_fresh_repository_bootstraps_default_categories_automatically(
    category_seed_context,
):
    container, config = category_seed_context

    with container.product_repository._get_connection() as conn:
        conn.execute(
            "DELETE FROM categories"
        )
        conn.commit()

    fresh = Container(config)

    categories = (
        fresh.product_repository.get_all_categories()
    )

    actual = [
        (
            category.id,
            category.name,
            category.sort_order,
        )
        for category in categories
    ]

    assert actual == EXPECTED_DEFAULT_CATEGORIES
