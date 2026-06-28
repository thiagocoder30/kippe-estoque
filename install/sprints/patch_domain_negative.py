import os
import sys
import re
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor
def patch_batch(content: str) -> str:
    pattern = re.compile(r'if self\.quantity < 0:\s+raise ValueError\(".*?"\)')
    new_validation = '''if self.quantity < 0 and not self.code.startswith("OVERDRAFT"):
            raise ValueError("Violação de Invariante: Lotes físicos não podem ser negativos.")'''
    return pattern.sub(new_validation, content)
def patch_product(content: str) -> str:
    if "allow_negative_stock" not in content:
        content = content.replace(
            "category_id: Optional[str] = None",
            "category_id: Optional[str] = None\n    allow_negative_stock: bool = False"
        )
        
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
    sys.exit(1)
