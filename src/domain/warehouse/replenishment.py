from dataclasses import dataclass
from typing import Optional
from src.domain.warehouse.smart_sheet import SkuSmartSheet
from src.security.exceptions import BusinessRuleViolation

@dataclass(frozen=True)
class ReplenishmentSuggestion:
    """
    Representa uma sugestão de compra (Reposição) gerada pelo Assistente.
    """
    sku: str
    current_available: int
    min_stock: int
    ideal_stock: int
    suggested_quantity: int
    urgency: str  # CRITICAL, HIGH, NORMAL

class ReplenishmentEngine:
    """
    Motor do Assistente Inteligente responsável por sugerir compras.
    Baseia-se no saldo disponível calculado pela Smart Sheet.
    """
    @staticmethod
    def calculate(sheet: SkuSmartSheet, min_stock: int, ideal_stock: int) -> Optional[ReplenishmentSuggestion]:
        if min_stock < 0 or ideal_stock < 0:
            raise BusinessRuleViolation("Parâmetros de estoque mínimo e ideal não podem ser negativos.")
            
        if ideal_stock <= min_stock:
            raise BusinessRuleViolation("O estoque ideal deve ser estritamente maior que o estoque mínimo.")

        available = sheet.available_balance
        
        # Se o saldo disponível ainda é seguro (acima do mínimo), não sugere compra
        if available > min_stock:
            return None

        # Calcula o quanto falta para atingir o cenário ideal
        deficit = ideal_stock - available
        
        # Define urgência
        urgency = "NORMAL"
        if available <= 0:
            urgency = "CRITICAL"
        elif available <= (min_stock * 0.5):
            urgency = "HIGH"

        return ReplenishmentSuggestion(
            sku=sheet.sku,
            current_available=available,
            min_stock=min_stock,
            ideal_stock=ideal_stock,
            suggested_quantity=deficit,
            urgency=urgency
        )
