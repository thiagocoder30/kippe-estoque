from dataclasses import dataclass, field
from typing import Dict
from src.domain.warehouse.ledger import InventoryAccount

@dataclass(frozen=True)
class BalanceProjection:
    """
    Read Model (CQRS).
    Representa a projeção do saldo em um dado momento.
    """
    total: int
    by_batch: Dict[str, int] = field(default_factory=dict)
    by_location: Dict[str, int] = field(default_factory=dict)

class BalanceEngine:
    """
    Domain Service responsável por calcular (projetar) o saldo
    a partir de um histórico imutável de transações (Event Sourcing).
    Nenhum saldo é armazenado estaticamente; tudo é matemática pura.
    """
    @staticmethod
    def calculate(account: InventoryAccount) -> BalanceProjection:
        total = 0
        by_batch: Dict[str, int] = {}
        by_location: Dict[str, int] = {}

        for entry in account.entries:
            total += entry.quantity
            
            # Projeção por Lote (Crucial para o futuro Allocation/FEFO)
            by_batch[entry.batch_id] = by_batch.get(entry.batch_id, 0) + entry.quantity
            
            # Projeção por Localização Física (Lean Topology: A1, FLOOR-LIMPEZA, etc.)
            by_location[entry.location_id] = by_location.get(entry.location_id, 0) + entry.quantity

        # Filtra locais/lotes que zeraram para limpar a projeção
        by_batch = {k: v for k, v in by_batch.items() if v != 0}
        by_location = {k: v for k, v in by_location.items() if v != 0}

        return BalanceProjection(
            total=total,
            by_batch=by_batch,
            by_location=by_location
        )
