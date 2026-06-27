from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
from .result import Result
@dataclass
class Product:
    id: str  
    name: str  
    quantity: int = 0  
    batches: Dict[str, Dict[str, Any]] = field(default_factory=dict)  
    unit_of_measure: str = "un"  
    status: str = "ATIVO"
    category_id: Optional[str] = None  # Ligação com a Classificação Mercantil
    def __post_init__(self):
        if not self.id or not isinstance(self.id, str) or len(self.id.strip()) == 0:
            raise ValueError("Violação de Invariante: O SKU do produto é estritamente obrigatório e imutável.")
        if not self.name or not isinstance(self.name, str) or len(self.name.strip()) == 0:
            raise ValueError("Violação de Invariante: O Nome comercial do produto não pode ser vazio.")
        if self.unit_of_measure not in ["un", "kg", "lt"]:
            raise ValueError(f"Violação de Invariante: Unidade de medida [{self.unit_of_measure}] inválida para o varejo.")
        if self.status not in ["ATIVO", "INATIVO"]:
            raise ValueError(f"Violação de Invariante: Status de comercialização [{self.status}] inconsistente.")
    def add_stock(self, amount: int, expiration_date: str, batch_code: str) -> Result[None, str]:
        if self.status == "INATIVO":
            return Result.fail("Operação Rejeitada: Bloqueio de catálogo. Não é permitido movimentar estoque de SKUs INATIVOS.")
        if amount <= 0:
            return Result.fail("Quantidade deve ser maior que zero.")
        if not batch_code:
            return Result.fail("O código do Lote é obrigatório.")
        try:
            exp_date = datetime.strptime(expiration_date, "%Y-%m-%d").date()
            if exp_date <= datetime.today().date():
                return Result.fail("BLOQUEIO DE DOCA: Mercadoria vencida ou vence hoje.")
        except ValueError:
            return Result.fail("Formato de data inválido (Use YYYY-MM-DD).")
        self.quantity += amount
        current_qty = self.batches.get(batch_code, {}).get('qty', 0)
        self.batches[batch_code] = {'exp': expiration_date, 'qty': current_qty + amount}
        return Result.ok(None)
    def remove_stock(self, amount: int) -> Result[None, str]:
        if self.status == "INATIVO":
            return Result.fail("Operação Rejeitada: Bloqueio de catálogo. SKU suspenso para movimentações.")
        if amount <= 0: return Result.fail("Quantidade inválida.")
        if self.quantity < amount: return Result.fail("Estoque físico insuficiente.")
        remaining = amount
        sorted_batches = sorted(self.batches.items(), key=lambda x: (x[1]['exp'], x[0]))
        for batch_code, data in sorted_batches:
            if remaining == 0: break
            batch_qty = data['qty']
            if batch_qty <= 0: continue
            if batch_qty >= remaining:
                self.batches[batch_code]['qty'] -= remaining
                remaining = 0
            else:
                remaining -= batch_qty
                self.batches[batch_code]['qty'] = 0
        self.batches = {k: v for k, v in self.batches.items() if v['qty'] > 0}
        self.quantity -= amount
        return Result.ok(None)
        
    def get_picking_instructions(self) -> list:
        sorted_batches = sorted(self.batches.items(), key=lambda x: (x[1]['exp'], x[0]))
        return [{"lote": k, "validade": v['exp'], "qtd_disponivel": v['qty']} for k, v in sorted_batches]
    def can_be_removed(self) -> bool:
        return self.quantity == 0
