from datetime import date
from src.domain.batch import Batch
from src.domain.services.fefo_allocator import FefoAllocator, OutOfStockException

def run_tests():
    # Setup
    b1 = Batch(batch_id="L001", sku="SKU-A", quantity=10, expiration_date=date(2026, 12, 1))
    b2 = Batch(batch_id="L002", sku="SKU-A", quantity=15, expiration_date=date(2026, 10, 1)) # Vence primeiro
    b3 = Batch(batch_id="L003", sku="SKU-A", quantity=5, expiration_date=date(2027, 1, 1))
    
    batches = [b1, b2, b3]
    
    # Execução
    allocations = FefoAllocator.allocate(batches, 20)
    
    # Validação FEFO
    assert allocations[0][0].batch_id == "L002", "Erro FEFO: L002 deveria ser o primeiro"
    assert allocations[0][1] == 15, "Erro de quantidade alocada no L002"
    
    assert allocations[1][0].batch_id == "L001", "Erro FEFO: L001 deveria ser o segundo"
    assert allocations[1][1] == 5, "Erro de quantidade alocada no L001"
    
    assert b1.quantity == 5, "Erro na mutação da entidade L001"
    assert b2.quantity == 0, "Erro na mutação da entidade L002"
    
    print("[+] Testes de Contrato FEFO: PASS")

if __name__ == "__main__":
    run_tests()
