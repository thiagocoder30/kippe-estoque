#!/usr/bin/env bash
# ==============================================================================
# KIPPE PLATFORM - SPRINT INV004: FEFO Allocation Engine
# DOMAIN: Inventory (PROGRAMA C)
# LAYER: Domain Services
# ==============================================================================
set -euo pipefail

echo "[*] KIPPE PLATFORM: Iniciando Sprint INV004 (FEFO Allocation Engine)..."

# ------------------------------------------------------------------------------
# 1. PREFLIGHT VALIDATION & INFRASTRUCTURE CHECKS
# ------------------------------------------------------------------------------
echo "[*] Executando Preflight Validation..."

mkdir -p src/domain/services
mkdir -p tests/domain
mkdir -p docs/checkpoints
mkdir -p install/lib
mkdir -p install/sprints

# Fallback/Mock do contrato INV003.1 caso não exista no ambiente atual
if [[ ! -f "src/domain/batch.py" ]]; then
    echo "[!] Aviso: src/domain/batch.py não encontrado. Recriando contrato estabilizado (INV003.1)..."
    cat << 'EOF' > src/domain/batch.py
from dataclasses import dataclass
from datetime import date

@dataclass
class Batch:
    batch_id: str
    sku: str
    quantity: int
    expiration_date: date
EOF
fi

if [[ ! -f "install/lib/validation.sh" ]]; then
    echo "[!] Aviso: install/lib/validation.sh não encontrado. Recriando Quality Gate..."
    cat << 'EOF' > install/lib/validation.sh
#!/usr/bin/env bash
echo "[*] Quality Gate: Validando AST via compileall..."
python3 -m compileall "$1" > /dev/null
if [ $? -eq 0 ]; then
    echo "[+] AST Validation OK para $1"
else
    echo "[-] Falha na validação AST para $1"
    exit 1
fi
EOF
    chmod +x install/lib/validation.sh
fi

# ------------------------------------------------------------------------------
# 2. DOMAIN SERVICE: FEFO ALLOCATOR (DDD)
# ------------------------------------------------------------------------------
echo "[*] Implementando Domain Service: FefoAllocator..."

cat << 'EOF' > src/domain/services/fefo_allocator.py
from typing import List, Tuple
from src.domain.batch import Batch

class OutOfStockException(Exception):
    """Exceção de domínio levantada quando a quantidade solicitada excede o estoque disponível."""
    pass

class FefoAllocator:
    """
    Motor de Alocação FEFO (First Expiring, First Out).
    Garante que os lotes com vencimento mais próximo sejam consumidos primeiro.
    Contrato Imutável (Frozen Contract).
    """
    
    @staticmethod
    def allocate(batches: List[Batch], required_quantity: int) -> List[Tuple[Batch, int]]:
        if required_quantity <= 0:
            raise ValueError("A quantidade solicitada deve ser maior que zero.")

        # Ordenação FEFO: Menor data de expiração primeiro
        sorted_batches = sorted(batches, key=lambda b: b.expiration_date)
        
        allocated_records: List[Tuple[Batch, int]] = []
        remaining_quantity = required_quantity
        
        for batch in sorted_batches:
            if remaining_quantity == 0:
                break
            if batch.quantity <= 0:
                continue
                
            allocation = min(batch.quantity, remaining_quantity)
            allocated_records.append((batch, allocation))
            
            # Mutação controlada da entidade Batch
            batch.quantity -= allocation
            remaining_quantity -= allocation
            
        if remaining_quantity > 0:
            raise OutOfStockException(
                f"Estoque insuficiente. Faltam {remaining_quantity} unidades para atender a demanda."
            )
            
        return allocated_records
EOF

# ------------------------------------------------------------------------------
# 3. COMPILER GATE & QUALITY ASSURANCE
# ------------------------------------------------------------------------------
echo "[*] Acionando Compiler Gate..."
./install/lib/validation.sh src/domain/services/fefo_allocator.py

# ------------------------------------------------------------------------------
# 4. TESTE DE CONTRATO (UNIT TEST)
# ------------------------------------------------------------------------------
echo "[*] Gerando e executando testes de contrato FEFO..."

cat << 'EOF' > tests/domain/test_fefo_allocator.py
from datetime import date
from src.domain.batch import Batch
from src.domain.services.fefo_allocator import FefoAllocator, OutOfStockException

def run_tests():
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
    
    print("[+] Testes de Contrato FEFO: PASS")

if __name__ == "__main__":
    run_tests()
EOF

python3 tests/domain/test_fefo_allocator.py

# ------------------------------------------------------------------------------
# 5. ATUALIZAÇÃO DE GOVERNANÇA E SCORECARD
# ------------------------------------------------------------------------------
echo "[*] Atualizando Scorecard e Estado do Projeto..."

cat << 'EOF' > docs/checkpoints/ARCHITECTURE_SCORECARD-INV004.md
# ARCHITECTURE SCORECARD - SPRINT INV004
## FEFO Allocation Engine

| Critério | Status | Observação |
|---|---|---|
| **Domain Driven Design** | PASS | Lógica isolada em `FefoAllocator` (Domain Service). |
| **Imutabilidade de Contrato** | PASS | Tipagem estrita mantida (`List[Tuple[Batch, int]]`). |
| **Compiler Gate** | PASS | AST validada via `compileall`. |
| **Testes de Regressão** | PASS | Validação de ordenação de datas e mutação de entidade. |

**Decisão Arquitetural:** O motor FEFO foi aprovado e integrado ao Domínio de Inventário.
EOF

cat << 'EOF' > ESTADO_PROJETO.md
# KIPPE PLATFORM - ESTADO DO PROJETO
* **Programa Atual:** PROGRAMA C (Inventory)
* **Última Sprint Concluída:** INV004 (FEFO Allocation Engine)
* **Status:** Motor de alocação FEFO implementado como Domain Service.
* **Próximo Passo Sugerido:** Sprint INV005 (Integração do FEFO com a Camada de Aplicação / Use Cases de Saída de Estoque).
EOF

echo "[+] Sprint INV004 concluída com sucesso. Artefatos gerados e validados."
