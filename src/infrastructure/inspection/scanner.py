import os
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class CapabilityTarget:
    name: str
    target_files: List[str]
    target_patterns: List[str]
    weight: int
    score: int = 0
    is_met: bool = False

class CapabilityScanner:
    """
    Inspeciona dinamicamente a base de código para mapear as capacidades ativas da plataforma.
    """
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.capabilities = self._define_matrix()

    def _define_matrix(self) -> Dict[str, List[CapabilityTarget]]:
        return {
            "DOMAIN": [
                CapabilityTarget("InventoryAccount", ["src/domain/warehouse/ledger.py"], ["class InventoryAccount"], 100),
                CapabilityTarget("Product", ["src/domain/catalog/product.py"], ["class Product"], 100),
                CapabilityTarget("Commands", ["src/application/warehouse/commands.py"], ["class ReceiveGoodsCommand"], 100),
                CapabilityTarget("Events", ["src/domain/warehouse/ledger.py"], ["_uncommitted_events"], 100)
            ],
            "APPLICATION": [
                CapabilityTarget("InventoryQueryService", ["src/application/warehouse/query_service.py"], ["class InventoryQueryService"], 100),
                CapabilityTarget("CommandBus", ["src/application/warehouse/command_bus.py"], ["class CommandBus"], 100),
                CapabilityTarget("ReplenishmentEngine", ["src/domain/warehouse/replenishment.py", "src/application/warehouse/query_service.py"], ["ReplenishmentEngine"], 100),
                CapabilityTarget("SmartSheetBuilder", ["src/domain/warehouse/smart_sheet.py"], ["class SmartSheetBuilder"], 100),
                CapabilityTarget("OperationalTruthEngine", ["src/domain/warehouse/operational_truth.py"], ["class OperationalTruthEngine"], 100),
                CapabilityTarget("InventoryAuditService", ["src/application/warehouse/audit_service.py"], ["class InventoryAuditService"], 100)
            ],
            "READ PROJECTIONS": [
                CapabilityTarget("InventoryProductView", ["src/application/warehouse/query_service.py"], ["class InventoryProductView"], 100)
            ],
            "SEARCH": [
                CapabilityTarget("SKU", ["src/presentation/cli/warehouse_cli.py"], ["def get_sku_view"], 100),
                CapabilityTarget("Description", ["src/application/warehouse/search_service.py"], ["def search_by_description"], 100),
                CapabilityTarget("Brand", ["src/application/warehouse/search_service.py"], ["def search_by_brand"], 100),
                CapabilityTarget("Supplier", ["src/application/warehouse/search_service.py"], ["def search_by_supplier"], 100),
                CapabilityTarget("Category", ["src/application/warehouse/search_service.py"], ["def search_by_category"], 100)
            ],
            "REPORTS": [
                CapabilityTarget("Dashboard", ["src/application/warehouse/dashboard_service.py"], ["class DashboardService"], 100),
                CapabilityTarget("Executive Report", ["src/presentation/reports/executive.py"], ["class ExecutiveReport"], 100),
                CapabilityTarget("Purchase Report", ["src/presentation/reports/purchase.py"], ["class PurchaseReport"], 100),
                CapabilityTarget("Expiration Report", ["src/presentation/reports/expiration.py"], ["class ExpirationReport"], 100)
            ],
            "OBSERVABILITY": [
                CapabilityTarget("Telemetry", ["src/infrastructure/monitoring/telemetry.py"], ["class TelemetryEngine"], 100),
                CapabilityTarget("AuditTrail", ["src/infrastructure/monitoring/telemetry.py"], ["class AuditTrail"], 100)
            ],
            "RELEASE": [
                CapabilityTarget("Certification", ["src/infrastructure/release/certification.py"], ["class ProductionCertificationEngine"], 100),
                CapabilityTarget("Manifest", ["src/infrastructure/release/certification.py"], ["RELEASE_MANIFEST.json"], 100)
            ]
        }

    def scan(self) -> Dict[str, List[CapabilityTarget]]:
        for category, targets in self.capabilities.items():
            for target in targets:
                target.score = 0
                for file_path in target.target_files:
                    full_path = os.path.join(self.root_dir, file_path.replace("/", os.sep))
                    if os.path.exists(full_path):
                        target.score += 50  # Arquivo existe
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            if any(re.search(pattern, content) for pattern in target.target_patterns):
                                target.score += 50  # Padrão encontrado
                                break
                target.is_met = target.score == 100
        return self.capabilities
