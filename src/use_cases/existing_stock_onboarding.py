from datetime import date
from typing import Optional

from src.domain.access_control import AccessControl
from src.domain.result import Result


class ExistingStockOnboardingUseCase:
    """
    Incorpora ao controle do Kippe uma quantidade que já existia
    fisicamente antes de ser registrada no sistema.

    Product/Batch continuam sendo a única autoridade quantitativa.
    A informação histórica opcional é evidência documental e nunca
    substitui o horário real em que a operação foi registrada.
    """

    EVENT_TYPE = "IMPLANTACAO_ESTOQUE"
    INVENTORY_SOURCE = "PHYSICAL_COUNT"

    HISTORICAL_BASIS_DOCUMENT = "DOCUMENT"
    HISTORICAL_BASIS_OPERATOR = "OPERATOR_DECLARATION"

    ALLOWED_ROLES = {
        AccessControl.ROLE_MANAGER,
        AccessControl.ROLE_SYSTEM_ADMIN,
        AccessControl.ROLE_SYSTEM,
    }

    def __init__(
        self,
        repository,
        identity_provider=None,
    ):
        self.repository = repository
        self.identity = identity_provider

    def _get_operator_id(self) -> str:
        if self.identity is None:
            return AccessControl.ROLE_SYSTEM

        return str(
            self.identity.get_current_operator_id()
            or ""
        ).strip()

    def _get_operator_role(self) -> str:
        if self.identity is None:
            return AccessControl.ROLE_SYSTEM

        return str(
            self.identity.get_current_operator_role()
            or ""
        ).strip()

    @staticmethod
    def _normalize_optional_text(
        value,
    ) -> str:
        return str(
            value or ""
        ).strip()

    @classmethod
    def _validate_historical_context(
        cls,
        *,
        historical_receipt_date,
        historical_date_basis,
        document_id,
    ):
        normalized_date = (
            cls._normalize_optional_text(
                historical_receipt_date
            )
        )

        normalized_basis = (
            cls._normalize_optional_text(
                historical_date_basis
            )
        )

        normalized_document = (
            cls._normalize_optional_text(
                document_id
            )
        )

        if (
            not normalized_date
            and not normalized_basis
        ):
            return Result.ok(
                {
                    "historical_receipt_date": None,
                    "historical_date_basis": None,
                    "document_id": normalized_document,
                }
            )

        if (
            normalized_date
            and not normalized_basis
        ):
            return Result.fail(
                "A data histórica exige uma base documental "
                "ou declaração explícita."
            )

        if (
            normalized_basis
            and not normalized_date
        ):
            return Result.fail(
                "A base histórica não pode ser informada "
                "sem a respectiva data."
            )

        allowed_basis = {
            cls.HISTORICAL_BASIS_DOCUMENT,
            cls.HISTORICAL_BASIS_OPERATOR,
        }

        if normalized_basis not in allowed_basis:
            return Result.fail(
                "Base da data histórica inválida."
            )

        try:
            parsed_date = date.fromisoformat(
                normalized_date
            )
        except (
            TypeError,
            ValueError,
        ):
            return Result.fail(
                "A data histórica deve usar o formato "
                "YYYY-MM-DD."
            )

        if parsed_date > date.today():
            return Result.fail(
                "A data histórica não pode estar no futuro."
            )

        if (
            normalized_basis
            == cls.HISTORICAL_BASIS_DOCUMENT
            and not normalized_document
        ):
            return Result.fail(
                "Uma data histórica baseada em documento "
                "exige o número do documento."
            )

        return Result.ok(
            {
                "historical_receipt_date": (
                    parsed_date.isoformat()
                ),
                "historical_date_basis": (
                    normalized_basis
                ),
                "document_id": (
                    normalized_document
                ),
            }
        )

    def execute(
        self,
        *,
        product_id: str,
        quantity: int,
        batch_code: str,
        expiration_date: str,
        manufacturing_date: str = "",
        supplier: str = "",
        location_id: str = "",
        historical_receipt_date: Optional[str] = None,
        historical_date_basis: Optional[str] = None,
        document_id: str = "",
    ) -> Result[dict, str]:
        operator_id = (
            self._get_operator_id()
        )

        operator_role = (
            self._get_operator_role()
        )

        if operator_role not in self.ALLOWED_ROLES:
            return Result.fail(
                "Operador sem privilégio para implantar "
                "estoque preexistente."
            )

        normalized_product_id = (
            self._normalize_optional_text(
                product_id
            )
        )

        normalized_batch_code = (
            self._normalize_optional_text(
                batch_code
            )
        )

        normalized_expiration_date = (
            self._normalize_optional_text(
                expiration_date
            )
        )

        normalized_manufacturing_date = (
            self._normalize_optional_text(
                manufacturing_date
            )
        )

        normalized_supplier = (
            self._normalize_optional_text(
                supplier
            )
        )

        normalized_location_id = (
            self._normalize_optional_text(
                location_id
            )
        )

        normalized_document_id = (
            self._normalize_optional_text(
                document_id
            )
        )

        if not normalized_product_id:
            return Result.fail(
                "Produto é obrigatório."
            )

        if not normalized_batch_code:
            return Result.fail(
                "Lote é obrigatório."
            )

        if not normalized_expiration_date:
            return Result.fail(
                "Validade é obrigatória."
            )

        try:
            normalized_quantity = int(
                quantity
            )
        except (
            TypeError,
            ValueError,
        ):
            return Result.fail(
                "Quantidade inválida."
            )

        if normalized_quantity <= 0:
            return Result.fail(
                "Quantidade deve ser maior que zero."
            )

        historical = (
            self._validate_historical_context(
                historical_receipt_date=(
                    historical_receipt_date
                ),
                historical_date_basis=(
                    historical_date_basis
                ),
                document_id=(
                    normalized_document_id
                ),
            )
        )

        if not historical.is_success:
            return historical

        product = self.repository.get_by_id(
            normalized_product_id
        )

        if product is None:
            return Result.fail(
                "Produto não encontrado."
            )

        if (
            normalized_batch_code
            in product.batches
        ):
            return Result.fail(
                "Este lote já existe para o produto e não "
                "pode ser implantado novamente."
            )

        quantity_before = int(
            product.quantity
        )

        stock_result = product.add_stock(
            amount=normalized_quantity,
            expiration_date=(
                normalized_expiration_date
            ),
            batch_code=(
                normalized_batch_code
            ),
            manufacturing_date=(
                normalized_manufacturing_date
            ),
            supplier=(
                normalized_supplier
            ),
            location_id=(
                normalized_location_id
            ),
        )

        if not stock_result.is_success:
            return Result.fail(
                stock_result.error
            )

        metadata = {
            "inventory_source": (
                self.INVENTORY_SOURCE
            ),
            "legacy_stock": True,
            "historical_receipt_date": (
                historical.value[
                    "historical_receipt_date"
                ]
            ),
            "historical_date_basis": (
                historical.value[
                    "historical_date_basis"
                ]
            ),
            "manufacturing_date": (
                normalized_manufacturing_date
            ),
            "expiration_date": (
                normalized_expiration_date
            ),
        }

        self.repository.save_product_with_operational_audit(
            product,
            event_type=self.EVENT_TYPE,
            product_id=product.id,
            batch_code=normalized_batch_code,
            location_id=normalized_location_id,
            quantity_planned=None,
            quantity_actual=normalized_quantity,
            quantity_before=quantity_before,
            quantity_after=product.quantity,
            quantity_divergence=None,
            supplier=normalized_supplier,
            document_id=(
                historical.value[
                    "document_id"
                ]
            ),
            origin_document=self.INVENTORY_SOURCE,
            operator_id=operator_id,
            metadata=metadata,
        )

        return Result.ok(
            {
                "status": "STOCK_ONBOARDED",
                "event_type": self.EVENT_TYPE,
                "product_id": product.id,
                "batch_code": normalized_batch_code,
                "quantity": normalized_quantity,
                "quantity_before": quantity_before,
                "quantity_after": product.quantity,
                "location_id": normalized_location_id,
                "supplier": normalized_supplier,
                "document_id": (
                    historical.value[
                        "document_id"
                    ]
                ),
                "historical_receipt_date": (
                    historical.value[
                        "historical_receipt_date"
                    ]
                ),
                "historical_date_basis": (
                    historical.value[
                        "historical_date_basis"
                    ]
                ),
            }
        )
