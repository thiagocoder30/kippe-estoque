#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM C: INVENTORY
# SPRINT INV016.1: NEGATIVE STOCK POLICIES (HOTFIX)
# ============================================================
set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"
# 1. Bootstrap (13-Step Frozen Framework)
source install/lib/bootstrap.sh
source install/lib/testing.sh
source install/lib/validation.sh
kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR
TOTAL_STEPS=4
kippe::banner_program "C" "INV016.1" "Negative Stock Policies (Stabilization)"
kippe::step 1 ${TOTAL_STEPS} "Applying Domain Mutations via AST-Safe Engine..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/sprints/patch_domain_negative.py"
import os
import sys
import re
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor
def patch_batch(content: str) -> str:
    # Substituição robusta usando Regex e Multi-line strings
    pattern = re.compile(r'if self\.quantity < 0:\s+raise ValueError\(".*?"\)')
    new_validation = '''if self.quantity < 0 and not self.code.startswith("OVERDRAFT"):
            raise ValueError("Violação de Invariante: Lotes físicos não podem ser negativos.")'''
    return pattern.sub(new_validation, content)
def patch_product(content: str) -> str:
    # Injeção da flag de permissão
    if "allow_negative_stock" not in content:
        content = content.replace(
            "category_id: Optional[str] = None",
            "category_id: Optional[str] = None\n    allow_negative_stock: bool = False"
        )
        
    # Substituição segura do método remove_stock inteiro via Regex
    pattern = re.compile(r'    def remove_stock\(self.*?return Result\.ok\(None\)', re.DOTALL)
    
    new_method = '''    def remove_stock(self, amount: int, operation_type: str = "DEFAULT", warehouse_id: str = "WH-PADRAO") -> Result[None, str]:
        if self.status == "INATIVO":
            return Result.fail("Operação Rejeitada: Bloqueio de catálogo. SKU suspenso para movimentações.")
        if amount <= 0: return Result.fail("Quantidade inválida.")
        from src.domain.services.negative_stock_policy import NegativeStockPolicyEngine
        auth = NegativeStockPolicyEngine.authorize_deduction(self, amount, operation_type)
        if not auth.is_success:
            return Result.fail(auth.error)
        from src.domain.services.fefo_selector import FEFOSelector
        eligible_batches = [b for b in FEFOSelector.get_eligible_batches(self.batches) if b.quantity > 0]
        
        remaining = amount
        for batch in eligible_batches:
            if remaining == 0: break
            if batch.quantity >= remaining:
                batch.quantity -= remaining
                remaining = 0
            else:
                remaining -= batch.quantity
                batch.quantity = 0
        if remaining > 0:
            overdraft_code = f"OVERDRAFT-{warehouse_id}"
            if overdraft_code in self.batches:
                self.batches[overdraft_code].quantity -= remaining
            else:
                from src.domain.batch import Batch
                self.batches[overdraft_code] = Batch(
                    code=overdraft_code, product_id=self.id, quantity=-remaining,
                    expiration_date="2099-12-31", warehouse_id=warehouse_id, location_id="VIRTUAL"
                )
            remaining = 0
        self.quantity -= amount
        return Result.ok(None)'''
    
    if "NegativeStockPolicyEngine" not in content:
        content = pattern.sub(new_method, content)
        
    return content
try:
    with SafeRefactor("src/domain/batch.py") as sr:
        sr.apply(patch_batch)
    with SafeRefactor("src/domain/product.py") as sr:
        sr.apply(patch_product)
except Exception as e:
    print(f"Abortando mutação de Agregados: {e}")
    sys.exit(1)
KIPPE_HUNK
python3 "${KIPPE_ROOT}/install/sprints/patch_domain_negative.py"
kippe::step 2 ${TOTAL_STEPS} "Implementing Negative Stock Policy Engine & SQLite Persistence..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/services/negative_stock_policy.py"
from src.domain.product import Product
from src.domain.result import Result
class NegativeStockPolicyEngine:
    """
    Domain Service: NegativeStockPolicyEngine
    Centraliza as regras corporativas de autorização para saldo negativo logístico.
    Integra com a trilha de auditoria para justificar exceções de backoffice.
    """
    @staticmethod
    def authorize_deduction(product: Product, amount: int, operation_type: str) -> Result[bool, str]:
        if product.quantity >= amount:
            return Result.ok(True)
            
        if not getattr(product, 'allow_negative_stock', False):
            return Result.fail(f"Estoque insuficiente. Política de Estoque Negativo DESATIVADA para o SKU {product.id}.")
            
        if operation_type == "TRANSFER":
            return Result.fail(f"Estoque insuficiente. Transferências logísticas não podem gerar saldo negativo (SKU {product.id}).")
            
        return Result.ok(True)
KIPPE_HUNK
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/sprints/patch_repo_negative.py"
import os
import sys
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor
def patch_repository(content: str) -> str:
    # Injeta a coluna no SQLite com segurança dict(row) para evitar o erro AttributeError da sqlite3.Row
    add_col = '''            cursor = conn.execute("PRAGMA table_info(products)")
            columns = [info['name'] for info in cursor.fetchall()]
            if 'allow_negative_stock' not in columns:
                conn.execute("ALTER TABLE products ADD COLUMN allow_negative_stock INTEGER NOT NULL DEFAULT 0")'''
    if "allow_negative_stock" not in content:
        content = content.replace("conn.commit()", add_col + "\n            conn.commit()", 1)
        
        content = content.replace(
            "category_id, reserved_quantity)",
            "category_id, reserved_quantity, allow_negative_stock)"
        )
        content = content.replace(
            "category_id=excluded.category_id, reserved_quantity=excluded.reserved_quantity",
            "category_id=excluded.category_id, reserved_quantity=excluded.reserved_quantity, allow_negative_stock=excluded.allow_negative_stock"
        )
        content = content.replace(
            "product.category_id, product.reserved_quantity))",
            "product.category_id, product.reserved_quantity, int(product.allow_negative_stock)))"
        )
        
        # O uso de dict() garante que não acionaremos o erro da sqlite3.Row não suportar .get()
        content = content.replace(
            "status=prod_row['status'], category_id=prod_row['category_id']",
            "status=prod_row['status'], category_id=prod_row['category_id'], allow_negative_stock=bool(dict(prod_row).get('allow_negative_stock', 0))"
        )
        content = content.replace(
            "status=row['status'], category_id=row['category_id']",
            "status=row['status'], category_id=row['category_id'], allow_negative_stock=bool(dict(row).get('allow_negative_stock', 0))"
        )
    return content
try:
    with SafeRefactor("src/interfaces/sqlite_repository.py") as sr:
        sr.apply(patch_repository)
except Exception as e:
    sys.exit(1)
KIPPE_HUNK
python3 "${KIPPE_ROOT}/install/sprints/patch_repo_negative.py"
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/test_negative_stock_policies.py"
import pytest
from src.domain.product import Product
from src.domain.batch import Batch
def test_negative_stock_blocked_by_default():
    p = Product(id="SKU-NEG-1", name="Monitor")
    p.add_stock(5, "2030-01-01", "L-1")
    
    # A tentativa de remover mais que o saldo disponível deve falhar por padrão
    res = p.remove_stock(10, operation_type="SALE")
    assert res.is_success is False
    assert "DESATIVADA" in res.error
def test_negative_stock_allowed_for_sales_creates_overdraft_batch():
    p = Product(id="SKU-NEG-2", name="Teclado", allow_negative_stock=True)
    p.add_stock(5, "2030-01-01", "L-2")
    
    # Política permitida para vendas transborda gerando saldo negativo
    res = p.remove_stock(15, operation_type="SALE", warehouse_id="WH-1")
    assert res.is_success is True
    assert p.quantity == -10
    
    # Lote de descoberto virtual foi criado para absorver a diferença
    assert "OVERDRAFT-WH-1" in p.batches
    assert p.batches["OVERDRAFT-WH-1"].quantity == -10
def test_negative_stock_blocked_for_transfers_even_if_policy_allowed():
    p = Product(id="SKU-NEG-3", name="Mouse", allow_negative_stock=True)
    p.add_stock(5, "2030-01-01", "L-3")
    
    # Transferências logísticas físicas não podem ser forçadas a transbordar
    res = p.remove_stock(10, operation_type="TRANSFER")
    assert res.is_success is False
    assert "Transferências logísticas não podem" in res.error
KIPPE_HUNK
# 3. Semantic Validator & 4. AST Compile
kippe::step 3 ${TOTAL_STEPS} "Verifying Code Integrity via Semantic and AST Gates..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
# 5. Regression Suite
kippe::step 4 ${TOTAL_STEPS} "Executing Core Regression Suite..."
kippe::test_execute_all
# 6. Architecture Scorecard
cat << "SCORECARD" > "${KIPPE_ROOT}/docs/checkpoints/ARCHITECTURE_SCORECARD-INV016.md"
# Architecture Scorecard - Kippe Platform
### Sprint: INV016.1 - Negative Stock Policies

| Critério | Status | Detalhes |
| :--- | :--- | :--- |
| **Testes passando** | ✅ | GREEN. Lógica de overdraft virtual (lotes negativos) atestada com sucesso. |
| **Overdraft Engine** | ✅ | Geração de lotes virtuais \`OVERDRAFT-WH-X\` isola débitos físicos em atraso. |
| **Policy Routing** | ✅ | \`NegativeStockPolicyEngine\` bloqueia transferências sem saldo independentemente da política. |
| **Gate C.4 (Analytics)** | ✅ | Base de inteligência transacional completada. |

SCORECARD
# 7. Checkpoint & 8. Manifest
kippe::checkpoint_create "054" "1.3.0-frozen" "INV016.1" "SUCCESS"
kippe::manifest_create "INV016.1" "C" "1.3.0-frozen" "SUCCESS" "INV017"
# Limpeza de scripts de mutação e transientes
rm -f "${KIPPE_ROOT}"/install/sprints/patch_*.py
rm -f data/test_*.db data/test_*.log data/test_*.db-journal 2>/dev/null || true
# 9 a 12. Sincronização Compulsória do Estado Permanente
kippe::governance_sync \
    "C" \
    "Inventory" \
    "2" \
    "Profissional" \
    "C.4" \
    "Analytics" \
    "INV016.1 (Negative Stock Policies Stabilization)" \
    "INV017 — Order Fulfillment Allocation" \
    "17/20 Sprints" \
    "STABLE"
exit 0
