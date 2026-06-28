from dataclasses import dataclass
from datetime import datetime, timedelta
@dataclass
class Reservation:
    """
    Entidade: Reservation (Lifecycle Edition)
    Gerencia Soft Allocation com expiração automática (TTL) e cancelamentos.
    """
    id: str
    product_id: str
    amount: int
    operator_id: str
    status: str = "PENDING"  # PENDING, FULFILLED, CANCELLED, EXPIRED
    created_at: str = ""
    expires_at: str = ""
    def __post_init__(self):
        if not self.id or len(self.id.strip()) == 0: raise ValueError("ID da Reserva é obrigatório.")
        if not self.product_id or len(self.product_id.strip()) == 0: raise ValueError("ID do Produto é obrigatório para reserva.")
        if self.amount <= 0: raise ValueError("A quantidade reservada deve ser maior que zero.")
        if self.status not in ["PENDING", "FULFILLED", "CANCELLED", "EXPIRED"]: raise ValueError("Status de reserva inválido.")
        
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        if not self.expires_at:
            # TTL Padrão da plataforma: 30 minutos de alocação de prateleira
            exp = datetime.strptime(self.created_at, "%Y-%m-%d %H:%M:%S") + timedelta(minutes=30)
            self.expires_at = exp.strftime("%Y-%m-%d %H:%M:%S")
    def is_expired(self) -> bool:
        if self.status != "PENDING": return False
        return datetime.now() > datetime.strptime(self.expires_at, "%Y-%m-%d %H:%M:%S")
    def cancel(self, reason: str = "CANCELLED") -> None:
        if self.status != "PENDING": raise ValueError(f"Não é possível alterar uma reserva no status {self.status}.")
        self.status = reason
    def fulfill(self) -> None:
        if self.status != "PENDING": raise ValueError(f"Não é possível efetivar uma reserva no status {self.status}.")
        self.status = "FULFILLED"
