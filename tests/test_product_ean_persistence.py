import os

from src.infrastructure.config import Config
from src.infrastructure.container import Container


def test_product_ean_survives_sqlite_persistence():

    config = Config.for_testing()
    container = Container(config)

    container.identity_provider.override_id = "SYSTEM-TEST-AGENT"
    container.identity_provider.override_role = "GERENTE"

    try:
        result = container.use_case.create_product(
            product_id="SKU-EAN-001",
            name="Leite Integral 1L",
            ean="7891234567890",
        )

        assert result.is_success

        product = container.product_repository.get_by_id(
            "SKU-EAN-001"
        )

        assert product is not None
        assert product.ean == "7891234567890"

        products = container.product_repository.get_all()

        reloaded = next(
            product
            for product in products
            if product.id == "SKU-EAN-001"
        )

        assert reloaded.ean == "7891234567890"

    finally:
        if os.path.exists(config.DB_PATH):
            os.remove(config.DB_PATH)

        if os.path.exists(config.LOG_PATH):
            os.remove(config.LOG_PATH)
