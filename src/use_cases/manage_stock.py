from typing import Any, Dict, List, Optional

from src.domain.access_control import AccessControl
from src.domain.product import Product
from src.domain.result import Result
from src.domain.services.inventory_adjustment_engine import (
    InventoryAdjustmentEngine,
)
from src.domain.services.putaway_engine import PutawayEngine
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

    def _log_info(self, msg: str):
        if self.logger:
            self.logger.info(msg)

    def _log_warn(self, msg: str):
        if self.logger:
            self.logger.warning(msg)

    def create_product(
        self,
        product_id: str,
        name: str,
        unit_of_measure: str = "un",
        status: str = "ATIVO",
        category_id: str = None,
        ean: str = "",
    ) -> Result[None, str]:
        op_id = self._get_op()
        op_role = self._get_role()

        if not AccessControl.can_manage_operational_catalog(
            op_role
        ):
            msg = (
                f"RBAC Block: Operador [{op_id}] tentou "
                f"cadastrar SKU [{product_id}] sem privilégios."
            )

            self._log_warn(msg)

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

        try:
            product = Product(
                id=product_id,
                name=name,
                ean=ean,
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

        return Result.ok(None)

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
                "total_quantity": product.quantity,
                "instructions": (
                    product.get_picking_instructions()
                ),
            }
        )

    def get_recent_history(
        self,
    ) -> List[Dict[str, Any]]:
        return self.repository.get_history()
