from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
from .result import Result
from .batch import Batch
from .services.fefo_selector import FEFOSelector

@dataclass
class Product:
    id: str  
    name: str  
    quantity: int = 0  
    reserved_quantity: int = 0
    batches: Dict[str, Batch] = field(default_factory=dict)  
    unit_of_measure: str = "un"  
    status: str = "ATIVO"
    category_id: Optional[str] = None  

    @property
    def available_quantity(self) -> int:
        return self.quantity - self.reserved_quantity

    def __post_init__(self):
        if not self.id or not isinstance(self.id, str) or len(self.id.strip()) == 0:
            raise ValueError("Violação de Invariante: O SKU do produto é estritamente obrigatório e imutável.")
        if not self.name or not isinstance(self.name, str) or len(self.name.strip()) == 0:
            raise ValueError("Violação de Invariante: O Nome comercial do produto não pode ser vazio.")
        if self.unit_of_measure not in ["un", "kg", "lt"]:
            raise ValueError(f"Violação de Invariante: Unidade de medida [{self.unit_of_measure}] inválida para o varejo.")
        if self.status not in ["ATIVO", "INATIVO"]:
            raise ValueError(f"Violação de Invariante: Status de comercialização [{self.status}] inconsistente.")

    def add_stock(self, amount: int, expiration_date: str, batch_code: str, manufacturing_date: str = "", supplier: str = "PADRAO", warehouse_id: str = "WH-PADRAO", location_id: str = "") -> Result[None, str]:
        if self.status == "INATIVO":
            return Result.fail("Operação Rejeitada: Bloqueio de catálogo. Não é permitido movimentar estoque de SKUs INATIVOS.")
        if amount <= 0:
            return Result.fail("Quantidade deve ser maior que zero.")
        if not batch_code:
            return Result.fail("O código do Lote é obrigatório.")
            
        try:
            new_batch = Batch(
                code=batch_code, product_id=self.id, quantity=amount,
                expiration_date=expiration_date, manufacturing_date=manufacturing_date, 
                supplier=supplier, warehouse_id=warehouse_id, location_id=location_id
            )
            if new_batch.is_expired():
                return Result.fail("BLOQUEIO DE DOCA: Mercadoria vencida ou vence hoje.")
        except ValueError as e:
            return Result.fail(str(e))

        self.quantity += amount
        if batch_code in self.batches:
            self.batches[batch_code].quantity += amount
        else:
            self.batches[batch_code] = new_batch
        return Result.ok(None)

    def remove_stock(self, amount: int) -> Result[None, str]:
        if self.status == "INATIVO":
            return Result.fail("Operação Rejeitada: Bloqueio de catálogo. SKU suspenso para movimentações.")
        if amount <= 0: return Result.fail("Quantidade inválida.")
        if self.quantity < amount: return Result.fail("Estoque físico insuficiente.")

        eligible_batches = [b for b in FEFOSelector.get_eligible_batches(self.batches) if b.quantity > 0]
        
        available_valid_qty = sum(b.quantity for b in eligible_batches)
        if available_valid_qty < amount:
            return Result.fail("Estoque insuficiente de lotes válidos (vencidos são bloqueados para saída).")
            
        remaining = amount
        for batch in eligible_batches:
            if remaining == 0: break
            if batch.quantity >= remaining:
                batch.quantity -= remaining
                remaining = 0
            else:
                remaining -= batch.quantity
                batch.quantity = 0

        self.quantity -= amount
        return Result.ok(None)
        
    def get_picking_instructions(self) -> list:
        eligible_batches = [b for b in FEFOSelector.get_eligible_batches(self.batches) if b.quantity > 0]
        return [{"lote": b.code, "validade": b.expiration_date, "qtd_disponivel": b.quantity} for b in eligible_batches]

    def get_stock_by_warehouse(self, warehouse_id: str) -> int:
        return sum(b.quantity for b in self.batches.values() if b.warehouse_id == warehouse_id)

    def get_available_stock_by_warehouse(self, warehouse_id: str) -> int:
        total_physical = self.quantity
        if total_physical == 0: return 0
        local_physical = self.get_stock_by_warehouse(warehouse_id)
        local_reserved = int((self.reserved_quantity * local_physical) / total_physical)
        return local_physical - local_reserved

    def can_be_removed(self) -> bool:
        return self.quantity == 0 and self.reserved_quantity == 0
