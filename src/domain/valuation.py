from dataclasses import dataclass, field
from datetime import datetime
@dataclass(frozen=True)
class InventoryValuationResult:
    """
    Entidade: InventoryValuationResult (Read Model Imutável)
    Representa a fotografia financeira do estoque em um dado momento.
    """
    product_id: str
    total_quantity: int
    total_value: float
    average_cost: float
    valuation_method: str
    valuation_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
