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
