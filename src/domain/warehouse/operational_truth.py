from dataclasses import dataclass
from typing import Literal, Dict

ActionPriority = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]

@dataclass(frozen=True)
class OperationalInsight:
    """O único artefato que o operador humano precisa ler."""
    sku: str
    title: str
    message: str
    priority: ActionPriority
    suggested_action: str

class OperationalTruthEngine:
    """
    Motor de Compressão de Decisão.
    Consome matemática complexa (E006-E009) e emite diretrizes táticas simplificadas.
    """
    @staticmethod
    def evaluate(
        sku: str,
        stock_total: int,
        divergence_penalty: float, # 0.0 (sem penalidade) a 1.0 (alta penalidade)
        trust_score: float,        # 0.0 (não confiável) a 1.0 (confiável)
        inbound_risk: float        # 0.0 (baixo risco) a 1.0 (alto risco na origem)
    ) -> OperationalInsight:
        
        # O cálculo funde a confiabilidade da história (trust), 
        # do presente (divergência) e do passado (origem)
        risk = (
            ((1.0 - trust_score) * 0.4) +
            (divergence_penalty * 0.4) +
            (inbound_risk * 0.2)
        )

        # Matriz de Decisão Operacional
        if risk > 0.8:
            priority = "CRITICAL"
            action = "PARALISAR COMPRAS. AUDITORIA IMEDIATA EXIGIDA."
        elif risk > 0.5:
            priority = "HIGH"
            action = "VERIFICAR FÍSICO ANTES DE QUALQUER NOVA MOVIMENTAÇÃO."
        elif risk > 0.3:
            priority = "MEDIUM"
            action = "MONITORIZAR SKU. PRECISÃO EM QUEDA."
        else:
            priority = "LOW"
            action = "OPERAÇÃO NORMAL."

        # Intervenção de Reposição Saudável (apenas se o risco for suportável)
        if stock_total < 10 and risk < 0.5:
            action = "CRIAR ORDEM DE REPOSIÇÃO (BAIXO RISCO OPERACIONAL)."
        elif stock_total < 10 and risk >= 0.5:
            action = "ESTOQUE BAIXO, MAS RISCO ALTO. AUDITAR ANTES DE COMPRAR."

        return OperationalInsight(
            sku=sku,
            title=f"STATUS {sku}: {priority}",
            message=f"Nível de Risco Operacional: {round(risk, 2)}",
            priority=priority,
            suggested_action=action
        )
