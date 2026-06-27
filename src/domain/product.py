from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime
from .result import Result

@dataclass
class Product:
    id: str
    name: str
    quantity: int
    # Estrutura: { 'LOTE123': {'exp': 'YYYY-MM-DD', 'qty': int} }
    batches: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def add_stock(self, amount: int, expiration_date: str, batch_code: str) -> Result[None, str]:
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
        if amount <= 0: return Result.fail("Quantidade inválida.")
        if self.quantity < amount: return Result.fail("Estoque físico insuficiente.")

        remaining = amount
        # Ordena cronologicamente pela data, desempata pelo código do lote
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

        # Limpeza atômica dos lotes vazios
        self.batches = {k: v for k, v in self.batches.items() if v['qty'] > 0}
        self.quantity -= amount
        return Result.ok(None)
        
    def get_picking_instructions(self) -> list:
        """Gera a lista de separação (Pick-List) para a gôndola ordenada por FEFO."""
        sorted_batches = sorted(self.batches.items(), key=lambda x: (x[1]['exp'], x[0]))
        return [{"lote": k, "validade": v['exp'], "qtd_disponivel": v['qty']} for k, v in sorted_batches]
