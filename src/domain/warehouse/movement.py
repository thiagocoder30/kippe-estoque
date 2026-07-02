from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, List, Dict, Any

from src.security.exceptions import BusinessRuleViolation


MovementType = Literal[
    "TO_STORE",
    "FROM_STORE",
    "CONSUMPTION",
    "ADJUSTMENT",
    "TRANSFER",
    "RETURN_TO_STOCK",
]


@dataclass(frozen=True)
class MovementEvent:
    sku: str
    quantity: int
    movement_type: MovementType
    origin: str
    destination: str
    reason: Optional[str]
    created_at: str


class DualStockView:
    """
    Calcula a visão Depot/Store tanto para eventos legados
    quanto para o Ledger moderno.

    O objetivo desta implementação é manter compatibilidade
    retroativa com toda a suíte de testes.
    """

    @staticmethod
    def calculate(
        events: List[Any],
        sku: str,
        base_depot_stock: int = 0,
    ) -> Dict[str, int]:

        depot = base_depot_stock
        store = 0

        for e in events:

            event_sku = getattr(
                e,
                "sku",
                getattr(e, "product_sku", None),
            )

            if event_sku and event_sku != sku:
                continue

            #
            # ======================================================
            # LEDGER MODERNO
            # ======================================================
            #
            if hasattr(e, "transaction_type"):

                qty = e.quantity
                tx = e.transaction_type.name

                if tx == "GOODS_RECEIPT":
                    depot += qty

                elif tx == "TRANSFER_OUT":
                    # quantidade negativa
                    depot += qty

                elif tx == "TRANSFER_IN":
                    # quantidade positiva
                    store += qty

                elif tx == "SALE":
                    # quantidade negativa
                    store += qty

                elif tx == "ADJUSTMENT":
                    location = getattr(
                        e,
                        "location_id",
                        "DEPOT",
                    )

                    if location == "STORE":
                        store += qty
                    else:
                        depot += qty

                elif tx == "CYCLE_COUNT":
                    location = getattr(
                        e,
                        "location_id",
                        "DEPOT",
                    )

                    if location == "STORE":
                        store += qty
                    else:
                        depot += qty

                continue

            #
            # ======================================================
            # MODELO LEGADO
            # ======================================================
            #
            qty = getattr(e, "quantity", 0)
            movement = getattr(e, "movement_type", None)

            if movement == "TO_STORE":
                depot -= qty
                store += qty

            elif movement in (
                "FROM_STORE",
                "RETURN_TO_STOCK",
            ):
                store -= qty
                depot += qty

            elif movement == "CONSUMPTION":
                store -= qty

            elif movement == "ADJUSTMENT":
                depot += qty

        return {
            "depot": depot,
            "store": store,
            "total": depot + store,
        }


class MovementEngine:
    @staticmethod
    def register(
        sku: str,
        quantity: int,
        movement_type: MovementType,
        origin: str,
        destination: str,
        reason: Optional[str] = None,
    ) -> MovementEvent:

        if quantity <= 0:
            raise BusinessRuleViolation(
                "A quantidade de movimentação deve ser estritamente positiva."
            )

        return MovementEvent(
            sku=sku,
            quantity=quantity,
            movement_type=movement_type,
            origin=origin,
            destination=destination,
            reason=reason,
            created_at=datetime.now().isoformat(),
        )
