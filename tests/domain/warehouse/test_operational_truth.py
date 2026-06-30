from src.domain.warehouse.operational_truth import OperationalTruthEngine

def test_operational_truth_evaluates_healthy_sku():
    insight = OperationalTruthEngine.evaluate(
        sku="CAFE-PILAO",
        stock_total=50,
        divergence_penalty=0.0,
        trust_score=1.0, # 100% confiável
        inbound_risk=0.0
    )
    
    assert insight.priority == "LOW"
    assert "OPERAÇÃO NORMAL" in insight.suggested_action

def test_operational_truth_evaluates_critical_risk():
    insight = OperationalTruthEngine.evaluate(
        sku="SABAO-PO",
        stock_total=100,
        divergence_penalty=0.9, # Alta divergência recente
        trust_score=0.2,        # Histórico terrível
        inbound_risk=0.8        # Lote cego (sem NF/Validade)
    )
    
    assert insight.priority == "CRITICAL"
    assert "PARALISAR COMPRAS" in insight.suggested_action

def test_operational_truth_blocks_blind_replenishment():
    # Estoque baixo (5), mas com risco elevado
    insight = OperationalTruthEngine.evaluate(
        sku="DETERGENTE",
        stock_total=5,
        divergence_penalty=0.6,
        trust_score=0.4,
        inbound_risk=0.5
    )
    
    assert insight.priority == "HIGH"
    assert "AUDITAR ANTES DE COMPRAR" in insight.suggested_action

def test_operational_truth_suggests_safe_replenishment():
    # Estoque baixo (5) num ambiente seguro
    insight = OperationalTruthEngine.evaluate(
        sku="LEITE",
        stock_total=5,
        divergence_penalty=0.0,
        trust_score=0.9,
        inbound_risk=0.1
    )
    
    assert insight.priority == "LOW"
    assert "CRIAR ORDEM DE REPOSIÇÃO" in insight.suggested_action
