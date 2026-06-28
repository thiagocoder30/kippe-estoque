from typing import List, Dict
from src.domain.batch import Batch
class FEFOSelector:
    """
    Domain Service: First Expiring, First Out (FEFO)
    Encapsula a política institucional de escoamento de perecíveis.
    """
    
    @staticmethod
    def get_eligible_batches(batches: Dict[str, Batch]) -> List[Batch]:
        valid_batches = [
            b for b in batches.values() 
            if b.quantity > 0 and not b.is_expired()
        ]
        
        return sorted(valid_batches, key=lambda b: (b.expiration_date, b.code))
