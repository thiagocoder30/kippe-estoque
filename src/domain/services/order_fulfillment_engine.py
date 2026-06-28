from typing import Dict, Any
from src.domain.product import Product
from src.domain.result import Result
class OrderFulfillmentAllocationEngine:
    """
    Domain Service: OrderFulfillmentAllocationEngine
    Orquestra o atendimento de pedidos (Fulfillment) garantindo a política de All-or-Nothing.
    Delega a baixa física/lógica e o tratamento de exceções (FEFO/Overdraft) de volta às Entidades.
    """
    @staticmethod
    def allocate_order(order_id: str, required_items: Dict[str, int], products_catalog: Dict[str, Product], operator_id: str, warehouse_id: str = "WH-PADRAO") -> Result[Dict[str, Any], str]:
        if not required_items:
            return Result.fail("O pedido não contém itens para alocação.")
        allocation_plan = {}
        # 1. Fase de Validação Pre-flight (All-or-Nothing)
        for sku, amount in required_items.items():
            if amount <= 0:
                return Result.fail(f"Quantidade inválida requerida para o SKU {sku}.")
            if sku not in products_catalog:
                return Result.fail(f"SKU {sku} não encontrado no catálogo de produtos.")
                
            product = products_catalog[sku]
            
            # Verificação prévia de disponibilidade considerando bloqueios
            if getattr(product, 'status', "ATIVO") == "INATIVO":
                return Result.fail(f"Falha de alocação: O SKU {sku} está INATIVO.")
                
            # A checagem de saldo bruto é delegada passivamente à Entidade no passo de execução, 
            # pois a entidade Product detém a verdade sobre as políticas de OVERDRAFT.
        # 2. Fase de Execução Transacional
        for sku, amount in required_items.items():
            product = products_catalog[sku]
            
            # Delega a complexidade da baixa para a árvore de decisão selada do Agregado Product (INV016.4)
            allocation_result = product.remove_stock(
                amount=amount, 
                operation_type="SALE", 
                warehouse_id=warehouse_id
            )
            
            if not allocation_result.is_success:
                # Em um sistema com banco de dados acoplado aqui, acionaríamos um rollback da transação.
                # Como o Domínio atua em memória antes da persistência, rejeitamos o pedido inteiro.
                return Result.fail(f"Falha na alocação do SKU {sku} (Pedido {order_id}): {allocation_result.error}")
                
            allocation_plan[sku] = amount
        # Retorna o plano de expedição aprovado
        return Result.ok({
            "order_id": order_id,
            "operator_id": operator_id,
            "warehouse_id": warehouse_id,
            "allocated_items": allocation_plan
        })
