import tempfile

from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.use_cases.manage_stock import ManageStockUseCase
from src.domain.result import Result


def test_putaway_use_case_updates_batch_location():

    with tempfile.NamedTemporaryFile() as db:

        repository = SQLiteProductRepository(db.name)
        repository._init_db()

        use_case = ManageStockUseCase(repository)

        create = use_case.create_product(
            "SKU-PUTAWAY",
            "Produto Putaway"
        )

        assert create.is_success

        receive = use_case.execute_add(
            "SKU-PUTAWAY",
            10,
            "2035-12-31",
            "LOTE-001"
        )

        assert receive.is_success

        result = use_case.execute_putaway(
            "SKU-PUTAWAY",
            "LOTE-001",
            "EST-A-01"
        )

        assert result.is_success

        product = repository.get_by_id("SKU-PUTAWAY")

        assert product.batches["LOTE-001"].location_id == "EST-A-01"
