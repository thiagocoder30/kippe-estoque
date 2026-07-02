from dataclasses import dataclass, field
from typing import Dict
from src.domain.warehouse.ledger import InventoryAccount


@dataclass(frozen=True)
class BalanceProjection:
    """
    Read Model (CQRS).
    Projeção institucional de estoque.
    """
    total: int
    by_batch: Dict[str, int] = field(default_factory=dict)
    by_location: Dict[str, int] = field(default_factory=dict)


class BalanceEngine:
    """
    Fonte única de verdade para cálculo de estoque.
    """

    @staticmethod
    def calculate(account: InventoryAccount) -> BalanceProjection:
        total = 0
        by_batch: Dict[str, int] = {}
        by_location: Dict[str, int] = {}

        for entry in account.entries:
            total += entry.quantity

            by_batch[entry.batch_id] = by_batch.get(entry.batch_id, 0) + entry.quantity
            by_location[entry.location_id] = by_location.get(entry.location_id, 0) + entry.quantity

        by_batch = {k: v for k, v in by_batch.items() if v != 0}
        by_location = {k: v for k, v in by_location.items() if v != 0}

        return BalanceProjection(
            total=total,
            by_batch=by_batch,
            by_location=by_location
        )
