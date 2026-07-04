"""
PATCH ADAPTER (não substituir router original ainda)
"""

from src.application.warehouse.snapshot.sku_snapshot_service import SKUSnapshotService
from src.presentation.api.snapshot.sku_snapshot_controller import SKUSnapshotController


class SnapshotRouterAdapter:

    def __init__(self, ledger_repo):
        self.service = SKUSnapshotService(ledger_repo)
        self.controller = SKUSnapshotController(self.service)

    def get_sku_snapshot(self, sku: str):
        return self.controller.get_sku_snapshot(sku)
