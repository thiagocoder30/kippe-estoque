from dataclasses import dataclass, field
from typing import List

from src.domain.warehouse.divergence import DivergenceEngine


@dataclass(frozen=True)
class CriticalSkuAudit:
    sku: str
    total_events: int
    total_adjustments: int
    unregistered_withdrawals: int
    compliance_status: str


@dataclass(frozen=True)
class InventoryAuditReport:
    total_skus_audited: int
    total_system_events: int
    critical_skus: List[CriticalSkuAudit] = field(default_factory=list)


class InventoryAuditService:
    """
    Serviço de aplicação responsável por consolidar sinais
    operacionais de auditoria a partir do Inventory Ledger.
    """

    def __init__(self, ledger_repo, catalog_repo=None):
        self.ledger_repo = ledger_repo
        self.catalog_repo = catalog_repo

    def run_global_audit(self, skus=None) -> InventoryAuditReport:
        if skus is None:
            accounts = list(self.ledger_repo.get_all())
        else:
            accounts = [
                self.ledger_repo.get_by_sku(sku)
                for sku in skus
            ]
            accounts = [
                account
                for account in accounts
                if account is not None
            ]

        total_events = 0
        critical_skus = []

        for account in accounts:
            entries = list(account.entries)
            total_events += len(entries)

            divergences = DivergenceEngine.extract_from_ledger(entries)

            total_adjustments = sum(
                1
                for entry in entries
                if getattr(
                    getattr(entry, "transaction_type", None),
                    "name",
                    None,
                ) == "ADJUSTMENT"
            )

            unregistered_withdrawals = sum(
                1
                for divergence in divergences
                if divergence.divergence_type
                == "UNREGISTERED_WITHDRAWAL"
            )

            adjustment_rate = (
                total_adjustments / len(entries)
                if entries
                else 0.0
            )

            if (
                adjustment_rate >= 0.5
                or unregistered_withdrawals >= 2
            ):
                compliance_status = "CRITICAL"

            elif (
                adjustment_rate >= 0.2
                or unregistered_withdrawals >= 1
            ):
                compliance_status = "WARNING"

            else:
                compliance_status = "COMPLIANT"

            if compliance_status == "CRITICAL":
                critical_skus.append(
                    CriticalSkuAudit(
                        sku=account.sku,
                        total_events=len(entries),
                        total_adjustments=total_adjustments,
                        unregistered_withdrawals=unregistered_withdrawals,
                        compliance_status=compliance_status,
                    )
                )

        return InventoryAuditReport(
            total_skus_audited=len(accounts),
            total_system_events=total_events,
            critical_skus=critical_skus,
        )
