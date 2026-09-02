from typing import Any, Dict, List, Optional

from src.domain.access_control import AccessControl
from src.domain.product import Product
from src.domain.result import Result
from src.domain.services.inventory_adjustment_engine import (
    InventoryAdjustmentEngine,
)
from src.domain.services.putaway_engine import PutawayEngine
from src.domain.services.fefo_selector import FEFOSelector
from src.domain.services.stock_transfer_engine import (
    StockTransferEngine,
)
from src.interfaces.identity import IdentityProvider
from src.interfaces.logger import Logger


class ManageStockUseCase:
    def __init__(
        self,
        repository,
        logger: Optional[Logger] = None,
        identity_provider: Optional[IdentityProvider] = None,
    ):
        self.repository = repository
        self.logger = logger
        self.identity = identity_provider

    def _get_op(self) -> str:
        return (
            self.identity.get_current_operator_id()
            if self.identity
            else AccessControl.ROLE_SYSTEM
        )

    def _get_role(self) -> str:
        return (
            self.identity.get_current_operator_role()
            if self.identity
            else AccessControl.ROLE_SYSTEM
        )

    def _log_info(
        self,
        msg: str,
    ):
        if self.logger:
            self.logger.info(
                msg
            )

    def _log_warn(
        self,
        msg: str,
    ):
        if self.logger:
            self.logger.warning(
                msg
            )

    def register_product(
        self,
        name: str,
        ean: str,
        unit_of_measure: str = "un",
        status: str = "ATIVO",
        category_id: str = None,
    ) -> Result[Dict[str, Any], str]:
        """
        Cadastro operacional de produto.

        O operador não fornece o SKU. A identidade interna é
        alocada atomicamente pela persistência.
        """
        op_id = self._get_op()
        op_role = self._get_role()

        if not AccessControl.can_manage_operational_catalog(
            op_role
        ):
            self._log_warn(
                f"RBAC Block: Operador [{op_id}] tentou "
                "cadastrar novo produto sem privilégios."
            )

            return Result.fail(
                "Autorização negada: Apenas GERENTES ou "
                "ADMINISTRADORES DO SISTEMA podem cadastrar "
                "novos SKUs."
            )

        normalized_name = str(
            name or ""
        ).strip()

        normalized_ean = str(
            ean or ""
        ).strip()

        normalized_unit = str(
            unit_of_measure or "un"
        ).strip().lower()

        normalized_status = str(
            status or "ATIVO"
        ).strip().upper()

        normalized_category = (
            str(category_id).strip()
            if category_id
            else None
        )

        if not normalized_name:
            return Result.fail(
                "A descrição do produto é obrigatória."
            )

        if not normalized_ean:
            return Result.fail(
                "O EAN é obrigatório para o cadastro operacional."
            )

        get_by_ean = getattr(
            self.repository,
            "get_by_ean",
            None,
        )

        if callable(
            get_by_ean
        ):
            existing = get_by_ean(
                normalized_ean
            )

            if existing:
                self._log_warn(
                    f"Cadastro Bloqueado: EAN "
                    f"[{normalized_ean}] já pertence ao "
                    f"SKU [{existing.id}]. "
                    f"Operador: [{op_id}]"
                )

                return Result.fail(
                    "EAN já cadastrado no produto "
                    f"[{existing.id}] {existing.name}."
                )

        register_new_product = getattr(
            self.repository,
            "register_new_product",
            None,
        )

        if not callable(
            register_new_product
        ):
            return Result.fail(
                "Repositório não suporta geração automática "
                "de SKU."
            )

        try:
            product = register_new_product(
                name=normalized_name,
                ean=normalized_ean,
                unit_of_measure=normalized_unit,
                status=normalized_status,
                category_id=normalized_category,
            )
        except ValueError as exc:
            self._log_warn(
                "Cadastro Bloqueado: "
                f"{str(exc)} "
                f"Operador: [{op_id}]"
            )

            return Result.fail(
                str(exc)
            )
        except Exception as exc:
            self._log_warn(
                "Falha de Persistência no cadastro "
                f"automático de produto: {str(exc)}. "
                f"Operador: [{op_id}]"
            )

            return Result.fail(
                "Não foi possível cadastrar o produto."
            )

        self.repository.log_transaction(
            product.id,
            "CRIACAO DE PRODUTO",
            0,
            op_id,
        )

        self._log_info(
            f"Produto Criado Automaticamente: "
            f"SKU [{product.id}] - "
            f"{product.name} "
            f"({product.unit_of_measure}/"
            f"{product.status}). "
            f"EAN [{product.ean}]. "
            f"Operador: [{op_id}]"
        )

        return Result.ok(
            {
                "id": product.id,
                "ean": product.ean,
                "name": product.name,
                "unit_of_measure": (
                    product.unit_of_measure
                ),
                "status": product.status,
                "category_id": (
                    product.category_id
                ),
            }
        )

    def create_product(
        self,
        product_id: str,
        name: str,
        unit_of_measure: str = "un",
        status: str = "ATIVO",
        category_id: str = None,
        ean: str = "",
    ) -> Result[None, str]:
        """
        Contrato legado/interno com SKU explícito.

        É preservado para compatibilidade de serviços, testes
        e integrações que já possuem uma identidade de produto.
        O fluxo operacional do frontend deve usar
        register_product().
        """
        op_id = self._get_op()
        op_role = self._get_role()

        if not AccessControl.can_manage_operational_catalog(
            op_role
        ):
            msg = (
                f"RBAC Block: Operador [{op_id}] tentou "
                f"cadastrar SKU [{product_id}] sem privilégios."
            )

            self._log_warn(
                msg
            )

            return Result.fail(
                "Autorização negada: Apenas GERENTES ou "
                "ADMINISTRADORES DO SISTEMA podem cadastrar "
                "novos SKUs."
            )

        if self.repository.get_by_id(
            product_id
        ):
            self._log_warn(
                f"Cadastro Bloqueado: SKU [{product_id}] "
                f"já existe. Operador: [{op_id}]"
            )

            return Result.fail(
                "Produto já cadastrado."
            )

        normalized_ean = str(
            ean or ""
        ).strip()

        if normalized_ean:
            get_by_ean = getattr(
                self.repository,
                "get_by_ean",
                None,
            )

            if callable(
                get_by_ean
            ):
                existing = get_by_ean(
                    normalized_ean
                )

                if existing:
                    self._log_warn(
                        f"Cadastro Bloqueado: EAN "
                        f"[{normalized_ean}] já pertence ao "
                        f"SKU [{existing.id}]. "
                        f"Operador: [{op_id}]"
                    )

                    return Result.fail(
                        "EAN já cadastrado no produto "
                        f"[{existing.id}] {existing.name}."
                    )

        try:
            product = Product(
                id=product_id,
                name=name,
                ean=normalized_ean,
                quantity=0,
                unit_of_measure=unit_of_measure,
                status=status,
                category_id=category_id,
            )
        except ValueError as exc:
            self._log_warn(
                "Validation Block: Falha de Invariante na "
                f"criação do SKU [{product_id}] - {str(exc)}"
            )

            return Result.fail(
                str(exc)
            )

        self.repository.save(
            product
        )

        self.repository.log_transaction(
            product_id,
            "CRIACAO DE PRODUTO",
            0,
            op_id,
        )

        self._log_info(
            f"Produto Criado: SKU [{product_id}] - "
            f"{name} ({unit_of_measure}/{status}). "
            f"Operador: [{op_id}]"
        )

        return Result.ok(
            None
        )

    def execute_add(
        self,
        product_id: str,
        amount: int,
        expiration_date: str,
        batch_code: str,
        manufacturing_date: str = "",
        supplier: str = "PADRAO",
    ) -> Result[None, str]:
        op_id = self._get_op()

        product = self.repository.get_by_id(
            product_id
        )

        if not product:
            self._log_warn(
                f"Entrada Bloqueada: SKU [{product_id}] "
                f"não encontrado. Operador: [{op_id}]"
            )

            return Result.fail(
                "Produto não encontrado."
            )

        res = product.add_stock(
            amount,
            expiration_date,
            batch_code,
            manufacturing_date,
            supplier,
        )

        if res.is_success:
            self.repository.save(
                product
            )

            self.repository.log_transaction(
                product_id,
                f"ENTRADA (Lote {batch_code})",
                amount,
                op_id,
            )

            self._log_info(
                f"Entrada Registrada: SKU [{product_id}] | "
                f"Lote [{batch_code}] | Qtd: {amount}. "
                f"Operador: [{op_id}]"
            )
        else:
            self._log_warn(
                f"Entrada Rejeitada pelo Domínio: "
                f"SKU [{product_id}] - {res.error}. "
                f"Operador: [{op_id}]"
            )

        return res

    def execute_putaway(
        self,
        product_id: str,
        batch_code: str,
        location_id: str,
    ) -> Result[None, str]:
        op_id = self._get_op()

        product = self.repository.get_by_id(
            product_id
        )

        if not product:
            self._log_warn(
                f"Putaway Bloqueado: SKU [{product_id}] "
                f"não encontrado. Operador: [{op_id}]"
            )

            return Result.fail(
                "Produto não encontrado."
            )

        res = PutawayEngine.execute_putaway(
            product,
            batch_code,
            location_id,
        )

        if res.is_success:
            self.repository.save(
                product
            )

            self.repository.log_transaction(
                product_id,
                f"PUTAWAY (Lote {batch_code} -> {location_id})",
                0,
                op_id,
            )

            self._log_info(
                f"Putaway Registrado: SKU [{product_id}] | "
                f"Lote [{batch_code}] | Local [{location_id}]. "
                f"Operador: [{op_id}]"
            )
        else:
            self._log_warn(
                f"Putaway Rejeitado: SKU [{product_id}] - "
                f"{res.error}. Operador: [{op_id}]"
            )

        return res

    def execute_remove(
        self,
        product_id: str,
        amount: int,
    ) -> Result[None, str]:
        op_id = self._get_op()

        product = self.repository.get_by_id(
            product_id
        )

        if not product:
            self._log_warn(
                f"Saída Bloqueada: SKU [{product_id}] "
                f"não encontrado. Operador: [{op_id}]"
            )

            return Result.fail(
                "Produto não encontrado."
            )

        res = product.remove_stock(
            amount
        )

        if res.is_success:
            self.repository.save(
                product
            )

            self.repository.log_transaction(
                product_id,
                "SAIDA (Baixa Automática FEFO)",
                amount,
                op_id,
            )

            self._log_info(
                f"Saída Registrada (FEFO): SKU [{product_id}] "
                f"| Qtd: {amount}. Operador: [{op_id}]"
            )
        else:
            self._log_warn(
                f"Saída Rejeitada pelo Domínio: "
                f"SKU [{product_id}] - {res.error}. "
                f"Operador: [{op_id}]"
            )

        return res

    def execute_transfer(
        self,
        product_id: str,
        amount: int,
        from_warehouse: str,
        to_warehouse: str,
    ) -> Result[None, str]:
        op_id = self._get_op()

        product = self.repository.get_by_id(
            product_id
        )

        if not product:
            self._log_warn(
                f"Transferência Bloqueada: SKU [{product_id}] "
                f"não encontrado. Operador: [{op_id}]"
            )

            return Result.fail(
                "Produto não encontrado."
            )

        res = StockTransferEngine.execute_transfer(
            product=product,
            amount=amount,
            from_warehouse=from_warehouse,
            to_warehouse=to_warehouse,
        )

        if res.is_success:
            self.repository.save(
                product
            )

            self.repository.log_transaction(
                product_id,
                (
                    "TRANSFERENCIA "
                    f"({from_warehouse} -> {to_warehouse})"
                ),
                amount,
                op_id,
            )

            self._log_info(
                f"Transferência Registrada: SKU [{product_id}] "
                f"| {from_warehouse} -> {to_warehouse} | "
                f"Qtd: {amount}. Operador: [{op_id}]"
            )
        else:
            self._log_warn(
                f"Transferência Rejeitada: SKU [{product_id}] "
                f"- {res.error}. Operador: [{op_id}]"
            )

        return res

    def execute_adjustment(
        self,
        product_id: str,
        amount: int,
        reason: str,
        batch_code: str = None,
        warehouse_id: str = "WH-PADRAO",
    ) -> Result[None, str]:
        op_id = self._get_op()

        product = self.repository.get_by_id(
            product_id
        )

        if not product:
            self._log_warn(
                f"Ajuste Bloqueado: SKU [{product_id}] "
                f"não encontrado. Operador: [{op_id}]"
            )

            return Result.fail(
                "Produto não encontrado."
            )

        res = InventoryAdjustmentEngine.execute_adjustment(
            product=product,
            amount=amount,
            reason=reason,
            operator_id=op_id,
            warehouse_id=warehouse_id,
            batch_code=batch_code,
        )

        if res.is_success:
            self.repository.save(
                product
            )

            self.repository.log_transaction(
                product_id,
                f"AJUSTE ({reason})",
                amount,
                op_id,
            )

            self._log_info(
                f"Ajuste Registrado: SKU [{product_id}] | "
                f"Motivo: [{reason}] | Qtd: {amount}. "
                f"Operador: [{op_id}]"
            )
        else:
            self._log_warn(
                f"Ajuste Rejeitado: SKU [{product_id}] - "
                f"{res.error}. Operador: [{op_id}]"
            )

        return res

    def list_all(
        self,
    ) -> List[Product]:
        return self.repository.get_all()

    def plan_replenishment(
        self,
        items,
    ) -> Result[Dict[str, Any], str]:
        """
        Monta um plano FEFO para abastecimento da loja.

        Este método é deliberadamente somente leitura:
        - não altera Product.quantity;
        - não altera Batch.quantity;
        - não persiste produto;
        - não registra transação.

        O carrinho representa intenção operacional. A baixa de
        estoque só ocorrerá em uma etapa posterior, após a
        confirmação física da coleta.

        SKUs repetidos são consolidados antes do cálculo FEFO.
        A ordem final preserva a primeira ocorrência de cada SKU.
        """
        if not isinstance(
            items,
            list,
        ) or not items:
            return Result.fail(
                "O carrinho de abastecimento está vazio."
            )

        consolidated = {}
        ordered_skus = []

        # ----------------------------------------------------
        # 1. Validar e consolidar carrinho
        # ----------------------------------------------------
        for raw_item in items:
            if not isinstance(
                raw_item,
                dict,
            ):
                return Result.fail(
                    "Item de abastecimento inválido."
                )

            product_id = str(
                raw_item.get(
                    "sku",
                    "",
                )
                or ""
            ).strip()

            if not product_id:
                return Result.fail(
                    "O SKU é obrigatório."
                )

            raw_quantity = raw_item.get(
                "quantity"
            )

            if (
                isinstance(
                    raw_quantity,
                    bool,
                )
                or not isinstance(
                    raw_quantity,
                    int,
                )
            ):
                return Result.fail(
                    "Quantidade inválida."
                )

            if raw_quantity <= 0:
                return Result.fail(
                    "Quantidade deve ser maior que zero."
                )

            if product_id not in consolidated:
                consolidated[
                    product_id
                ] = raw_quantity

                ordered_skus.append(
                    product_id
                )
            else:
                consolidated[
                    product_id
                ] += raw_quantity

        # ----------------------------------------------------
        # 2. Resolver FEFO sobre quantidades já consolidadas
        # ----------------------------------------------------
        planned_items = []

        for product_id in ordered_skus:
            requested_quantity = (
                consolidated[
                    product_id
                ]
            )

            product = self.repository.get_by_id(
                product_id
            )

            if not product:
                return Result.fail(
                    f"Produto [{product_id}] não encontrado."
                )

            eligible_batches = (
                FEFOSelector.get_eligible_batches(
                    product.batches
                )
            )

            available_quantity = sum(
                batch.quantity
                for batch in eligible_batches
            )

            if (
                available_quantity
                < requested_quantity
            ):
                return Result.fail(
                    "Estoque insuficiente de lotes válidos."
                )

            remaining = (
                requested_quantity
            )

            allocations = []

            for batch in eligible_batches:
                if remaining <= 0:
                    break

                allocated_quantity = min(
                    batch.quantity,
                    remaining,
                )

                allocations.append(
                    {
                        "batch_code": (
                            batch.code
                        ),
                        "expiration_date": (
                            batch.expiration_date
                        ),
                        "quantity": (
                            allocated_quantity
                        ),
                        "location_id": (
                            batch.location_id
                        ),
                    }
                )

                remaining -= (
                    allocated_quantity
                )

            planned_items.append(
                {
                    "sku": product.id,
                    "name": product.name,
                    "requested_quantity": (
                        requested_quantity
                    ),
                    "allocations": allocations,
                }
            )

        return Result.ok(
            {
                "items": planned_items
            }
        )

    def plan_replenishment_pick(
        self,
        items,
    ) -> Result[Dict[str, Any], str]:
        """
        Converte o plano FEFO de abastecimento em uma rota
        operacional de coleta.

        Responsabilidades:
        - reutilizar integralmente a resolução FEFO;
        - exigir endereço físico para todo lote alocado;
        - ordenar os passos por location_id;
        - preservar lote, validade e quantidade FEFO;
        - não alterar nem persistir estoque.
        """
        replenishment_plan = (
            self.plan_replenishment(
                items
            )
        )

        if not replenishment_plan.is_success:
            return Result.fail(
                replenishment_plan.error
            )

        steps = []

        for item in (
            replenishment_plan
            .value["items"]
        ):
            for allocation in (
                item["allocations"]
            ):
                location_id = str(
                    allocation.get(
                        "location_id",
                        "",
                    )
                    or ""
                ).strip()

                if not location_id:
                    return Result.fail(
                        "Lote FEFO sem endereçamento "
                        "físico para coleta."
                    )

                steps.append(
                    {
                        "location_id": (
                            location_id
                        ),
                        "sku": item["sku"],
                        "name": item["name"],
                        "batch_code": (
                            allocation[
                                "batch_code"
                            ]
                        ),
                        "expiration_date": (
                            allocation[
                                "expiration_date"
                            ]
                        ),
                        "quantity": (
                            allocation[
                                "quantity"
                            ]
                        ),
                    }
                )

        steps.sort(
            key=lambda step: (
                step["location_id"],
                step["sku"],
                step["batch_code"],
            )
        )

        for index, step in enumerate(
            steps,
            start=1,
        ):
            step["sequence"] = index

        return Result.ok(
            {
                "steps": steps
            }
        )

    def get_picking_info(
        self,
        product_id: str,
    ) -> Result[Dict[str, Any], str]:
        product = self.repository.get_by_id(
            product_id
        )

        if not product:
            return Result.fail(
                "Produto sem cadastro."
            )

        return Result.ok(
            {
                "name": product.name,
                "total_quantity": (
                    product.quantity
                ),
                "instructions": (
                    product.get_picking_instructions()
                ),
            }
        )

    def get_recent_history(
        self,
    ) -> List[Dict[str, Any]]:
        return self.repository.get_history()
