from dataclasses import dataclass
from typing import Optional

# ==========================================
# COMMANDS (Intenções de Escrita Imutáveis)
# ==========================================

@dataclass(frozen=True)
class ReceiveGoodsCommand:
    sku: str
    quantity: int
    supplier: str
    batch_code: str
    expiration_date: Optional[str]
    invoice_id: Optional[str]
    operator: str

@dataclass(frozen=True)
class TransferToStoreCommand:
    sku: str
    quantity: int
    batch_code: str
    operator: str

@dataclass(frozen=True)
class RegisterAdjustmentCommand:
    sku: str
    quantity: int
    batch_code: str
    divergence_type: str
    reason: str
    operator: str
