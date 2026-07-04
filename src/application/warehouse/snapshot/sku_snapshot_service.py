from src.application.warehouse.snapshot.sku_snapshot_builder import SKUSnapshotBuilder


class SKUSnapshotService:

    def __init__(self, ledger_repo, catalog=None):
        self.ledger_repo = ledger_repo
        self.catalog = catalog

    def get_snapshot(self, sku: str, min_stock: int = 40, ideal_stock: int = 120):
        account = self.ledger_repo.get_by_sku(sku)

        if not account:
            raise Exception(f"SKU {sku} não encontrado no ledger.")

        return SKUSnapshotBuilder.build(
            account=account,
            sku=sku,
            min_stock=min_stock,
            ideal_stock=ideal_stock
        )
