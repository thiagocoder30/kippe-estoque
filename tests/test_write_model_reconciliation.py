import os

from src.infrastructure.config import Config
from src.infrastructure.container import Container


def build_container():
    cfg = Config.for_testing()

    container = Container(config_override=cfg)
    container.product_repository._init_db()

    container.identity_provider.override_id = "RECOVERY-TEST"
    container.identity_provider.override_role = "GERENTE"

    return container, cfg


def cleanup(cfg):
    if os.path.exists(cfg.DB_PATH):
        os.remove(cfg.DB_PATH)
    if os.path.exists(cfg.LOG_PATH):
        os.remove(cfg.LOG_PATH)


def test_transfer_persists_on_canonical_product_batch_model():
    container, cfg = build_container()

    try:
        created = container.use_case.create_product(
            "SKU-TRANSFER",
            "Produto Transferência",
        )
        assert created.is_success

        received = container.use_case.execute_add(
            "SKU-TRANSFER",
            100,
            "2035-12-31",
            "L-001",
            supplier="FORNECEDOR",
        )
        assert received.is_success

        product = container.product_repository.get_by_id("SKU-TRANSFER")
        product.batches["L-001"].warehouse_id = "WH-PADRAO"
        container.product_repository.save(product)

        transferred = container.use_case.execute_transfer(
            "SKU-TRANSFER",
            40,
            "WH-PADRAO",
            "LOJA",
        )
        assert transferred.is_success

        persisted = container.product_repository.get_by_id("SKU-TRANSFER")

        assert persisted.quantity == 100
        assert persisted.get_stock_by_warehouse("WH-PADRAO") == 60
        assert persisted.get_stock_by_warehouse("LOJA") == 40

    finally:
        cleanup(cfg)


def test_adjustment_persists_on_canonical_product_batch_model():
    container, cfg = build_container()

    try:
        created = container.use_case.create_product(
            "SKU-ADJUST",
            "Produto Ajuste",
        )
        assert created.is_success

        received = container.use_case.execute_add(
            "SKU-ADJUST",
            20,
            "2035-12-31",
            "L-ADJ",
        )
        assert received.is_success

        adjusted = container.use_case.execute_adjustment(
            "SKU-ADJUST",
            -5,
            "AVARIA",
            batch_code="L-ADJ",
        )
        assert adjusted.is_success

        persisted = container.product_repository.get_by_id("SKU-ADJUST")

        assert persisted.quantity == 15
        assert persisted.batches["L-ADJ"].quantity == 15

    finally:
        cleanup(cfg)
