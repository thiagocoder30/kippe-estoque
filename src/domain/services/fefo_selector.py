from typing import List, Dict
from src.domain.batch import Batch
class FEFOSelector:
    """
    Domain Service: First Expiring, First Out (FEFO)
    Encapsula a política institucional de escoamento de perecíveis.
    """
    
    @staticmethod
    def get_eligible_batches(batches: Dict[str, Batch], warehouse_id: str = None) -> List[Batch]:
        valid_batches = [
            b for b in batches.values() 
            if b.quantity > 0 and not b.is_expired() and (warehouse_id is None or b.warehouse_id == warehouse_id)
        ]
        return sorted(valid_batches, key=lambda b: (b.expiration_date, b.code))
