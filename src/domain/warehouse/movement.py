from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, List, Dict
from src.security.exceptions import BusinessRuleViolation

MovementType = Literal[
    "TO_STORE",
    "FROM_STORE",
    "CONSUMPTION",
    "ADJUSTMENT",
    "TRANSFER",
    "RETURN_TO_STOCK"
]

@dataclass(frozen=True)
class MovementEvent:
    """
    Evento ultra-leve de registro de movimentação operacional.
    Focado na captura em <5s para garantir adesão.
    """
    sku: str
    quantity: int
    movement_type: MovementType
    origin: str          # ex: "REPOSITOR_APP", "AUDIT"
    destination: str     # ex: "STORE", "DEPOT"
    reason: Optional[str]
    created_at: str

class DualStockView:
    """
    CQRS Read Model para o Estoque Dual (Depósito vs Loja).
    Calcula a realidade particionada a partir dos micro-registros.
    """
    @staticmethod
    def calculate(events: List[MovementEvent], sku: str, base_depot_stock: int = 0) -> Dict[str, int]:
        depot = base_depot_stock
        store = 0

        for e in events:
            if e.sku != sku:
                continue

            if e.movement_type == "TO_STORE":
                depot -= e.quantity
                store += e.quantity
            elif e.movement_type in ("FROM_STORE", "RETURN_TO_STOCK"):
                store -= e.quantity
                depot += e.quantity
            elif e.movement_type == "CONSUMPTION":
                store -= e.quantity
            elif e.movement_type == "ADJUSTMENT":
                depot += e.quantity

        return {
            "depot": depot,
            "store": store,
            "total": depot + store
        }

class MovementEngine:
    """
    Fábrica de registro rápido para evitar a geração de divergências silenciosas.
    """
    @staticmethod
    def register(sku: str, quantity: int, movement_type: MovementType, origin: str, destination: str, reason: Optional[str] = None) -> MovementEvent:
        if quantity <= 0:
            raise BusinessRuleViolation("A quantidade de movimentação deve ser estritamente positiva.")
            
        return MovementEvent(
            sku=sku,
            quantity=quantity,
            movement_type=movement_type,
            origin=origin,
            destination=destination,
            reason=reason,
            created_at=datetime.now().isoformat()
        )
