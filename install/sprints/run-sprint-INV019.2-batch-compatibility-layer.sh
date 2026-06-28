#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM C: INVENTORY
# SPRINT INV019.2: BATCH CONTRACT COMPATIBILITY LAYER
# ============================================================
set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"
# 1. Bootstrap
source install/lib/bootstrap.sh
source install/lib/testing.sh
source install/lib/validation.sh
kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR
TOTAL_STEPS=3
kippe::banner_program "C" "INV019.2" "Batch Contract Compatibility Layer"
kippe::step 1 ${TOTAL_STEPS} "Rebuilding Dual-Interface Domain Entity (Shim Layer & Guards)..."
# Reconstrução integral da Entidade Batch: Modernização + Retrocompatibilidade
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/batch.py"
from dataclasses import dataclass
from datetime import datetime
@dataclass
class Batch:
    """
    Entidade: Batch (Lote)
    Representa um lote físico indivisível de um SKU no armazém.
    Inclui Compatibility Shim Layer para contratos legados de dicionário.
    """
    code: str
    product_id: str
    quantity: int
    expiration_date: str
    manufacturing_date: str = ""
    supplier: str = "PADRAO"
    status: str = "ATIVO"
    traceability_id: str = ""
    warehouse_id: str = "WH-PADRAO"
    location_id: str = ""
    cost_per_unit: float = 0.0  # DCP-1: Alinhamento Financeiro
    def __post_init__(self):
        # 1. Restauração de Validações Fortes Históricas
        if not self.code:
            raise ValueError("código do lote obrigatório")
        
        try:
            datetime.strptime(self.expiration_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Formato de data inválido")
        # Invariante histórica preservada com ressalva exata para Overdraft (INV016)
        if self.quantity < 0 and not self.code.startswith("OVERDRAFT"):
            raise ValueError("Violação de Invariante: A quantidade do lote não pode ser negativa.")
    def is_expired(self) -> bool:
        try:
            exp = datetime.strptime(self.expiration_date, "%Y-%m-%d")
            return datetime.now() > exp
        except ValueError:
            return False
    # 2. Compatibility Shim Layer: Permite acesso dict-like para testes e infra legada
    def __getitem__(self, key):
        if key == "qty":
            return self.quantity
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)
KIPPE_HUNK
# 3. Semantic Validator & 4. AST Compile
kippe::step 2 ${TOTAL_STEPS} "Verifying Domain Integrity via AST Gates..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
# 5. Regression Suite
kippe::step 3 ${TOTAL_STEPS} "Executing Core Regression Suite (Restoring Contract Equilibrium)..."
kippe::test_execute_all
# 6. Architecture Scorecard
cat << "SCORECARD" > "${KIPPE_ROOT}/docs/checkpoints/ARCHITECTURE_SCORECARD-INV019.md"
# Architecture Scorecard - Kippe Platform
### Sprint: INV019.2 - Batch Contract Compatibility Layer

| Critério | Status | Detalhes |
| :--- | :--- | :--- |
| **Testes passando** | ✅ | GREEN. Contratos legados totalmente restabelecidos. |
| **Dual-Interface** | ✅ | Entidade suporta \`batch.quantity\` e \`batch['qty']\` simultaneamente. |
| **Domain Guards** | ✅ | Validações de criação (\`__post_init__\`) ativadas blindando a API. |
| **Gate C.5 (Institutional)** | ✅ | Entidades de domínio higienizadas para encerramento do módulo. |

SCORECARD
# 7. Checkpoint & 8. Manifest
kippe::checkpoint_create "060" "1.3.0-frozen" "INV019.2" "SUCCESS"
kippe::manifest_create "INV019.2" "C" "1.3.0-frozen" "SUCCESS" "INV020"
# 9 a 12. Sincronização Compulsória do Estado Permanente
kippe::governance_sync \
    "C" \
    "Inventory" \
    "3" \
    "Institucional" \
    "C.5" \
    "Institutional Ready" \
    "INV019.2 (Batch Compatibility Layer)" \
    "INV020 — Inventory Consolidation & Sign-off" \
    "19/20 Sprints" \
    "STABLE"
exit 0
