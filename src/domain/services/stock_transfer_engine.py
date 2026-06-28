from src.domain.product import Product
from src.domain.result import Result
from src.domain.batch import Batch
from src.domain.services.fefo_selector import FEFOSelector
class StockTransferEngine:
    """
    Domain Service: Stock Transfer Engine
    Orquestra o remanejamento físico de mercadorias entre armazéns da rede.
    Preserva a invariante de massa global do Agregado de Produto.
    """
    @staticmethod
    def execute_transfer(product: Product, amount: int, from_warehouse: str, to_warehouse: str) -> Result[None, str]:
        if product.status == "INATIVO":
            return Result.fail("Operação Rejeitada: SKU suspenso no catálogo.")
        if amount <= 0:
            return Result.fail("A quantidade para transferência deve ser maior que zero.")
        if from_warehouse == to_warehouse:
            return Result.fail("Operação Inválida: Os armazéns de origem e destino devem ser distintos.")
        # 1. Valida saldo disponível local deduzindo reservas logísticas daquela planta
        available_origin = product.get_available_stock_by_warehouse(from_warehouse)
        if available_origin < amount:
            return Result.fail(f"Estoque insuficiente na origem [{from_warehouse}]. Disponível: {available_origin}, Solicitado: {amount}")
        # 2. Coleta os lotes da origem usando ordenação FEFO local
        eligible_batches = FEFOSelector.get_eligible_batches(product.batches, warehouse_id=from_warehouse)
        
        remaining = amount
        for batch in eligible_batches:
            if remaining == 0: break
            
            moved_qty = min(batch.quantity, remaining)
            
            # Débito físico na planta de origem
            batch.quantity -= moved_qty
            
            # Crédito físico na planta de destino
            target_batch_code = f"{batch.code}-TR-{to_warehouse}"
            if target_batch_code in product.batches:
                product.batches[target_batch_code].quantity += moved_qty
            else:
                product.batches[target_batch_code] = Batch(
                    code=target_batch_code,
                    product_id=product.id,
                    quantity=moved_qty,
                    expiration_date=batch.expiration_date,
                    warehouse_id=to_warehouse,
                    location_id="DOCA-TRANSITO",
                    manufacturing_date=batch.manufacturing_date,
                    supplier=batch.supplier,
                    traceability_id=batch.traceability_id
                )
            
            remaining -= moved_qty
        return Result.ok(None)
