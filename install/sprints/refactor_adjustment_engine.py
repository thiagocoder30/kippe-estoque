import os
import sys
from pathlib import Path
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor
def inject_adjustment_engine(content: str) -> str:
    engine_code = '''from src.domain.product import Product
from src.domain.result import Result
from src.domain.batch import Batch
class InventoryAdjustmentEngine:
    # Domain Service: InventoryAdjustmentEngine
    # Orquestra a reconciliacao entre o estoque fisico real e o saldo sistemico.
    # Registra motivos operacionais e audita a operacao.
    
    VALID_REASONS = ["AVARIA", "PERDA", "SOBRA", "VENCIMENTO", "CONTAGEM"]
    @staticmethod
    def execute_adjustment(product: Product, amount: int, reason: str, operator_id: str, warehouse_id: str = "WH-PADRAO", batch_code: str = None) -> Result[None, str]:
        if product.status == "INATIVO":
            return Result.fail("Operação Rejeitada: SKU inativo.")
        if reason not in InventoryAdjustmentEngine.VALID_REASONS:
            return Result.fail(f"Motivo de ajuste invalido. Permitidos: {InventoryAdjustmentEngine.VALID_REASONS}")
        if not operator_id or len(operator_id.strip()) == 0:
            return Result.fail("Operador responsavel e estritamente obrigatorio para auditoria.")
        if amount == 0:
            return Result.fail("A quantidade de ajuste nao pode ser zero.")
            
        # Ajuste Negativo (Perda, Avaria, etc)
        if amount < 0:
            abs_amount = abs(amount)
            if batch_code:
                if batch_code not in product.batches:
                    return Result.fail(f"Lote {batch_code} nao encontrado.")
                if product.batches[batch_code].quantity < abs_amount:
                    return Result.fail(f"Estoque insuficiente no lote {batch_code}.")
                product.batches[batch_code].quantity -= abs_amount
                product.quantity -= abs_amount
            else:
                res = product.remove_stock(abs_amount)
                if not res.is_success:
                    return Result.fail(res.error)
        
        # Ajuste Positivo (Sobra, Contagem para mais)
        else:
            if not batch_code:
                return Result.fail("Ajustes positivos requerem um lote (batch_code).")
            if batch_code in product.batches:
                product.batches[batch_code].quantity += amount
                product.quantity += amount
            else:
                import datetime
                long_exp = (datetime.date.today() + datetime.timedelta(days=365)).strftime("%Y-%m-%d")
                product.batches[batch_code] = Batch(
                    code=batch_code,
                    product_id=product.id,
                    quantity=amount,
                    expiration_date=long_exp,
                    warehouse_id=warehouse_id,
                    location_id="AJUSTE"
                )
                product.quantity += amount
        return Result.ok(None)
'''
    engine_path = Path(os.environ["KIPPE_ROOT"]) / "src" / "domain" / "services" / "inventory_adjustment_engine.py"
    engine_path.write_text(engine_code, encoding="utf-8")
    return content
try:
    with SafeRefactor("src/domain/services/__init__.py") as sr:
        sr.apply(inject_adjustment_engine)
except Exception as e:
    print(f"Abortando mutacao: {e}")
    sys.exit(1)
