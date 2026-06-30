from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Any

@dataclass(frozen=True)
class ProcurementEvent:
    """Representação imutável de um evento atômico no ciclo de vida de compras."""
    event_id: str
    event_type: str
    aggregate_id: str
    payload: Any
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

class SupplierLedger:
    """Livro-razão imutável e append-only exclusivo do Bounded Context de Procurement."""
    def __init__(self):
        self._events: List[ProcurementEvent] = []

    def append_event(self, event_id: str, event_type: str, aggregate_id: str, payload: Any) -> ProcurementEvent:
        allowed_types = [
            "SupplierCreated", "PurchaseOrderCreated", "PurchaseApproved",
            "GoodsReceived", "InvoiceReceived", "ThreeWayMatchSucceeded",
            "ThreeWayMatchFailed", "SupplierBlocked", "SupplierReactivated"
        ]
        if event_type not in allowed_types:
            raise ValueError(f"Tipo de evento inválido para o SupplierLedger: {event_type}")
            
        event = ProcurementEvent(
            event_id=event_id,
            event_type=event_type,
            aggregate_id=aggregate_id,
            payload=payload
        )
        self._events.append(event)
        return event

    def get_events_by_aggregate(self, aggregate_id: str) -> List[ProcurementEvent]:
        return [e for e in self._events if e.aggregate_id == aggregate_id]

    def get_events_by_type(self, event_type: str) -> List[ProcurementEvent]:
        return [e for e in self._events if e.event_type == event_type]

    @property
    def all_events(self) -> List[ProcurementEvent]:
        return list(self._events)
