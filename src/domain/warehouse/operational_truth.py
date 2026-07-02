from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any


class ActionPriority(str, Enum):
    LOW = "LOW"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class OperationalInsight:
    priority: ActionPriority
    reason: str
    suggested_action: str


class OperationalTruthEngine:

    ACTION_REASON = {
        ActionPriority.LOW: "OK",
        ActionPriority.HIGH: "BLOQUEIO PARCIAL",
        ActionPriority.CRITICAL: "RISCO CRÍTICO"
    }

    @staticmethod
    def evaluate(
        sku: str,
        stock_total: float,
        divergence_penalty: float,
        trust_score: float,
        inbound_risk: float,
        account: Optional[Any] = None  # compatível com query_service
    ) -> OperationalInsight:

        # -----------------------------
        # RISK SCORE
        # -----------------------------
        risk_score = (
            divergence_penalty * 0.35 +
            (1 - trust_score) * 0.35 +
            inbound_risk * 0.30
        )

        # -----------------------------
        # PRIORIDADE
        # -----------------------------
        if risk_score < 0.3:
            priority = ActionPriority.LOW
        elif risk_score < 0.7:
            priority = ActionPriority.HIGH
        else:
            priority = ActionPriority.CRITICAL

        # -----------------------------
        # CONTEXTO INSTITUCIONAL DE ESTOQUE
        # -----------------------------
        if priority == ActionPriority.LOW:
            if stock_total <= 10:
                suggested_action = "CRIAR ORDEM DE REPOSIÇÃO"
            else:
                suggested_action = "OPERAÇÃO NORMAL"

        elif priority == ActionPriority.HIGH:
            suggested_action = "AUDITAR ANTES DE COMPRAR"

        else:
            suggested_action = "PARALISAR COMPRAS"

        return OperationalInsight(
            priority=priority,
            reason=OperationalTruthEngine.ACTION_REASON[priority],
            suggested_action=suggested_action
        )
