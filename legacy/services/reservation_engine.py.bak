from src.domain.product import Product
from src.domain.reservation import Reservation
from src.domain.result import Result
import uuid
class ReservationEngine:
    """
    Domain Service: Orquestra o ciclo de vida das alocações de estoque.
    Previne venda a descoberto (Overselling) avaliando a quantidade disponível real.
    """
    
    @staticmethod
    def create_reservation(product: Product, amount: int, operator_id: str) -> Result[Reservation, str]:
        if product.status == "INATIVO":
            return Result.fail("Operação Rejeitada: Não é possível reservar produtos inativos.")
            
        if product.available_quantity < amount:
            return Result.fail(f"Estoque insuficiente. Físico: {product.quantity} | Disponível: {product.available_quantity} | Solicitado: {amount}")
            
        res_id = f"RES-{uuid.uuid4().hex[:8].upper()}"
        
        try:
            reservation = Reservation(id=res_id, product_id=product.id, amount=amount, operator_id=operator_id)
        except ValueError as e:
            return Result.fail(str(e))
            
        # Bloqueia a quantidade no agregado raiz
        product.reserved_quantity += amount
        return Result.ok(reservation)
    @staticmethod
    def cancel_reservation(product: Product, reservation: Reservation) -> Result[None, str]:
        if reservation.product_id != product.id:
            return Result.fail("A reserva não pertence a este produto.")
            
        try:
            reservation.cancel()
        except ValueError as e:
            return Result.fail(str(e))
            
        # Devolve a quantidade ao pool disponível
        product.reserved_quantity -= reservation.amount
        return Result.ok(None)
    @staticmethod
    def commit_reservation(product: Product, reservation: Reservation) -> Result[None, str]:
        """Efetiva a reserva, consumindo o estoque físico via política padrão do produto."""
        if reservation.product_id != product.id:
            return Result.fail("A reserva não pertence a este produto.")
            
        try:
            reservation.fulfill()
        except ValueError as e:
            return Result.fail(str(e))
            
        # Libera a trava lógica e realiza a baixa física real no Agregado
        product.reserved_quantity -= reservation.amount
        return product.remove_stock(reservation.amount)

    @staticmethod
    def purge_expired_reservations(product: Product, reservations: list[Reservation]) -> int:
        """
        Varre as reservas ativas, identifica as expiradas (TTL estourado),
        marca como EXPIRED e devolve o saldo lógico para o Product Aggregate.
        Retorna o total de itens devolvidos à gôndola lógica.
        """
        restored_amount = 0
        for res in reservations:
            if res.status == "PENDING" and res.is_expired():
                res.cancel(reason="EXPIRED")
                product.reserved_quantity -= res.amount
                restored_amount += res.amount
        return restored_amount
