#!/usr/bin/env bash
# ==============================================================================
# KIPPE PLATFORM - SPRINT INV004.1: Testing Infrastructure Standardization
# DOMAIN: Cross-Cutting / Infrastructure
# LAYER: Quality Gates
# ==============================================================================
set -euo pipefail

echo "[*] KIPPE PLATFORM: Iniciando Sprint INV004.1 (Testing Infrastructure Standardization)..."

# ------------------------------------------------------------------------------
# 1. PREFLIGHT VALIDATION & INFRASTRUCTURE CHECKS
# ------------------------------------------------------------------------------
echo "[*] Executando Preflight Validation..."

export KIPPE_ROOT="${KIPPE_ROOT:-$PWD}"
mkdir -p install/lib tests/domain docs/checkpoints install/sprints

# Garantir que o pytest esteja disponível no ambiente Termux/CLI
if ! python3 -m pytest --version > /dev/null 2>&1; then
    echo "[!] pytest não encontrado. Instalando dependência de infraestrutura..."
    python3 -m pip install -q pytest
fi

# ------------------------------------------------------------------------------
# 2. PADRONIZAÇÃO DO RUNNER DE TESTES (TESTING GATE)
# ------------------------------------------------------------------------------
echo "[*] Criando biblioteca de testes padronizada (install/lib/testing.sh)..."

cat << 'EOF' > install/lib/testing.sh
#!/usr/bin/env bash
# KIPPE PLATFORM - Testing Infrastructure

kippe::run_pytest() {
    export KIPPE_ROOT="${KIPPE_ROOT:-$PWD}"
    export PYTHONPATH="${KIPPE_ROOT}:${PYTHONPATH:-}"
    
    echo "[*] Quality Gate: Executando testes via pytest (PYTHONPATH=$PYTHONPATH)..."
    python3 -m pytest "$@"
}
EOF
chmod +x install/lib/testing.sh

# ------------------------------------------------------------------------------
# 3. REFATORAÇÃO DO TESTE FEFO PARA PADRÃO PYTEST
# ------------------------------------------------------------------------------
echo "[*] Refatorando tests/domain/test_fefo_allocator.py para o padrão pytest..."

cat << 'EOF' > tests/domain/test_fefo_allocator.py
from datetime import date
from src.domain.batch import Batch
from src.domain.services.fefo_allocator import FefoAllocator, OutOfStockException

def test_fefo_allocation():
    # Setup
    b1 = Batch(batch_id="L001", sku="SKU-A", quantity=10, expiration_date=date(2026, 12, 1))
    b2 = Batch(batch_id="L002", sku="SKU-A", quantity=15, expiration_date=date(2026, 10, 1)) # Vence primeiro
    b3 = Batch(batch_id="L003", sku="SKU-A", quantity=5, expiration_date=date(2027, 1, 1))
    
    batches = [b1, b2, b3]
    
    # Execução
    allocations = FefoAllocator.allocate(batches, 20)
    
    # Validação FEFO
    assert allocations[0][0].batch_id == "L002", "Erro FEFO: L002 deveria ser o primeiro"
    assert allocations[0][1] == 15, "Erro de quantidade alocada no L002"
    
    assert allocations[1][0].batch_id == "L001", "Erro FEFO: L001 deveria ser o segundo"
    assert allocations[1][1] == 5, "Erro de quantidade alocada no L001"
    
    assert b1.quantity == 5, "Erro na mutação da entidade L001"
    assert b2.quantity == 0, "Erro na mutação da entidade L002"
EOF

# ------------------------------------------------------------------------------
# 4. EXECUÇÃO DO QUALITY GATE (TESTES)
# ------------------------------------------------------------------------------
echo "[*] Acionando Testing Gate..."
source install/lib/testing.sh
kippe::run_pytest tests/domain/test_fefo_allocator.py -q

# ------------------------------------------------------------------------------
# 5. ATUALIZAÇÃO DE GOVERNANÇA E SCORECARD
# ------------------------------------------------------------------------------
echo "[*] Atualizando Scorecard e Estado do Projeto..."

cat << 'EOF' > docs/checkpoints/ARCHITECTURE_SCORECARD-INV004.1.md
# ARCHITECTURE SCORECARD - SPRINT INV004.1
## Testing Infrastructure Standardization

| Critério | Status | Observação |
|---|---|---|
| **Isolamento de Infraestrutura** | PASS | Runner de testes isolado em `install/lib/testing.sh`. |
| **Resolução de Dependências** | PASS | `PYTHONPATH` dinamicamente injetado via `KIPPE_ROOT`. |
| **Padronização de Testes** | PASS | Adoção do `pytest` como motor oficial de asserções. |

**Decisão Arquitetural:** O erro de `ModuleNotFoundError` foi mitigado na raiz da infraestrutura. O contrato de testes passa a ser estritamente via `kippe::run_pytest`.
EOF

cat << 'EOF' > ESTADO_PROJETO.md
# KIPPE PLATFORM - ESTADO DO PROJETO
* **Programa Atual:** PROGRAMA C (Inventory)
* **Última Sprint Concluída:** INV004.1 (Testing Infrastructure Standardization)
* **Status:** Motor FEFO validado com a nova infraestrutura de testes padronizada (pytest + PYTHONPATH).
* **Próximo Passo Sugerido:** Sprint INV005 (Integração do FEFO com a Camada de Aplicação / Use Cases de Saída de Estoque).
EOF

echo "[+] Sprint INV004.1 concluída com sucesso. Infraestrutura de testes estabilizada."
