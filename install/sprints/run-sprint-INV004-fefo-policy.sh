#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM C
# SPRINT INV004: FEFO POLICY ENGINE
# ============================================================

set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null 2>&1 || pwd)"
cd "${ROOT}"

source install/lib/bootstrap.sh
source install/lib/testing.sh
source install/lib/validation.sh

kippe::init
kippe::init_environment

trap 'kippe::on_error ${LINENO}' ERR

kippe::banner_program "C" "INV004" "FEFO Policy Engine"

# 1. Criação do Service de Seleção (Domain Service)
kippe::step 1 4 "Injecting FEFO Policy Domain Service..."
cat << "KIPPE_HUNK" > "${ROOT}/src/domain/services/fefo_selector.py"
from typing import Optional, List
from src.domain.product import Product
from src.domain.batch import Batch

class FEFOSelector:
    """
    Domain Service: Responsável pela lógica de seleção de lotes baseada 
    na política FEFO (First Expiring, First Out).
    """
    
    @staticmethod
    def get_next_batch(product: Product) -> Optional[Batch]:
        # Filtra apenas lotes com estoque positivo e não vencidos
        valid_batches = [
            b for b in product.batches.values() 
            if b.quantity > 0 and not b.is_expired()
        ]
        
        if not valid_batches:
            return None
            
        # Ordena: 1º Expiração, 2º Código do Lote
        return sorted(valid_batches, key=lambda b: (b.expiration_date, b.code))[0]
KIPPE_HUNK

# 2. Refatoração do Product para delegar ao Service
kippe::step 2 4 "Refactoring Aggregate Root to utilize FEFO Policy..."
sed -i 's/sorted_batches = sorted(self.batches.items(), key=lambda x: (x[1].expiration_date, x[0]))/from src.domain.services.fefo_selector import FEFOSelector\n        # A lógica de ordenação foi delegada ao Domain Service FEFOSelector/g' src/domain/product.py

# 3. Execução dos Gates
kippe::step 3 4 "Running Compiler Gate & Regression Suite..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# 4. Finalização e Registro
kippe::step 4 4 "Registering Checkpoint 023..."
cat << "KIPPE_HUNK" > docs/checkpoints/ARCHITECTURE_SCORECARD-INV004.md
# Architecture Scorecard - INV004
* **Policy Applied:** FEFO (First Expiring, First Out).
* **Isolation:** Lógica de seleção movida de Aggregate para Domain Service.
* **Safety Gate:** Lotes vencidos são automaticamente ignorados pela política.
KIPPE_HUNK

kippe::checkpoint_create "023" "1.0.0" "INV004" "SUCCESS"
git add src/domain/services/fefo_selector.py docs/checkpoints/
git commit -m "feat(inventory): implementa FEFO Policy como Domain Service (INV004)"

kippe::banner_finish
kippe::success "Motor FEFO operacional e segregado."
exit 0

