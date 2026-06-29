from dataclasses import dataclass, field
from typing import List, Dict
from src.domain.procurement.order import PurchaseOrder
from src.domain.procurement.invoice import SupplierInvoice

@dataclass(frozen=True)
class MatchResult:
    """
    Value Object: Resultado imutável da conciliação.
    Não altera o estado do pedido, apenas expõe a auditoria matemática.
    """
    is_matched: bool
    divergences: List[str] = field(default_factory=list)
    quantity_delta: Dict[str, int] = field(default_factory=dict)
    price_delta: Dict[str, float] = field(default_factory=dict)

class ThreeWayMatchEngine:
    """
    Domain Service: Avalia a tríade (1. Pedido Aprovado vs 2. Recebimento Físico vs 3. Fatura)
    """
    @staticmethod
    def evaluate(order: PurchaseOrder, invoice: SupplierInvoice) -> MatchResult:
        divergences = []
        q_delta = {}
        p_delta = {}

        # 1. Validação de Vínculo de Fornecedor
        if order.supplier_id != invoice.supplier_id:
            divergences.append("Fornecedor da nota fiscal difere do fornecedor do pedido de compra.")

        order_lines = {item.sku: item for item in order.items}
        
        for inv_line in invoice.lines:
            po_line = order_lines.get(inv_line.sku)
            
            # 2. Validação de Escopo (Item não solicitado)
            if not po_line:
                divergences.append(f"SKU {inv_line.sku} faturado, mas não consta no pedido de compra.")
                continue
            
            # 3. Validação de Três Pontas: Quantidade (Faturado vs Fisicamente Recebido)
            if inv_line.quantity != po_line.received_quantity:
                delta = inv_line.quantity - po_line.received_quantity
                q_delta[inv_line.sku] = delta
                divergences.append(
                    f"Divergência de quantidade no SKU {inv_line.sku}: Faturado={inv_line.quantity}, "
                    f"Fisicamente Recebido={po_line.received_quantity}."
                )

            # 4. Validação de Preço (Faturado vs Pedido Aprovado)
            if inv_line.unit_price.amount != po_line.unit_price.amount:
                delta_price = inv_line.unit_price.amount - po_line.unit_price.amount
                p_delta[inv_line.sku] = delta_price
                divergences.append(
                    f"Divergência de preço no SKU {inv_line.sku}: Faturado={inv_line.unit_price.amount}, "
                    f"Aprovado no Pedido={po_line.unit_price.amount}."
                )

        is_matched = len(divergences) == 0
        return MatchResult(
            is_matched=is_matched,
            divergences=divergences,
            quantity_delta=q_delta,
            price_delta=p_delta
        )
