from src.infrastructure.config import Config
from src.infrastructure.logger_adapter import FileLogger
from src.infrastructure.identity import CurrentOperatorResolver
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.interfaces.sqlite_operator_repository import SQLiteOperatorRepository
from src.infrastructure.document_storage import InvoiceDocumentStorage
from src.use_cases.manage_stock import ManageStockUseCase
from src.use_cases.receive_stock import ReceivingUseCase
from src.use_cases.existing_stock_onboarding import ExistingStockOnboardingUseCase
from src.use_cases.query_product import ProductQueryUseCase
from src.use_cases.suggest_products import ProductSuggestionUseCase
from src.use_cases.manage_operators import ManageOperatorsUseCase
from src.use_cases.manage_categories import ManageCategoriesUseCase
from src.use_cases.document_attachment import AttachDocumentToAuditEventUseCase
from src.application.procurement.invoice_preparation import (
    InvoicePreparationService,
)
from src.application.procurement.invoice_reconciliation import (
    CatalogReconciliationService,
)
from src.application.procurement.unresolved_product_workflow import (
    UnresolvedProductWorkflowService,
)
from src.application.procurement.product_onboarding_orchestration import (
    HumanProductOnboardingOrchestrator,
)
from src.application.procurement.post_onboarding_rereconciliation import (
    PostOnboardingRereconciliationService,
)
class Container:
    def __init__(self, config_override: Config = None):
        self.config = config_override or Config()
        self._logger = None
        self._identity_provider = None
        self._product_repository = None
        self._document_storage = None
        self._document_attachment_use_case = None
        self._operator_repository = None
        self._manage_stock_use_case = None
        self._receiving_use_case = None
        self._existing_stock_onboarding_use_case = None
        self._product_query_use_case = None
        self._product_suggestion_use_case = None
        self._manage_operators_use_case = None
        self._manage_categories_use_case = None
        self._invoice_preparation = None
        self._invoice_reconciliation = None
        self._unresolved_product = None
        self._product_onboarding = None
        self._post_onboarding = None
    @property
    def logger(self) -> FileLogger:
        if not self._logger: self._logger = FileLogger(self.config.LOG_PATH)
        return self._logger
    @property
    def identity_provider(self) -> CurrentOperatorResolver:
        if not self._identity_provider: self._identity_provider = CurrentOperatorResolver(self.config.ENV)
        return self._identity_provider

    @property
    def document_storage(self):
        if self._document_storage is None:
            self._document_storage = InvoiceDocumentStorage(
                root_path=self.config.DOCUMENT_ROOT,
            )
        return self._document_storage

    @property
    def document_attachment_use_case(self):
        if self._document_attachment_use_case is None:
            self._document_attachment_use_case = (
                AttachDocumentToAuditEventUseCase(
                    repository=self.product_repository,
                    storage=self.document_storage,
                )
            )
        return self._document_attachment_use_case

    @document_attachment_use_case.setter
    def document_attachment_use_case(self, value):
        self._document_attachment_use_case = value

    @property
    def product_repository(self) -> SQLiteProductRepository:
        if not self._product_repository: self._product_repository = SQLiteProductRepository(self.config.DB_PATH)
        return self._product_repository
    @property
    def operator_repository(self) -> SQLiteOperatorRepository:
        if not self._operator_repository: self._operator_repository = SQLiteOperatorRepository(self.config.DB_PATH)
        return self._operator_repository
    @property
    def use_case(self) -> ManageStockUseCase:
        if not self._manage_stock_use_case:
            self._manage_stock_use_case = ManageStockUseCase(
                repository=self.product_repository, logger=self.logger, identity_provider=self.identity_provider
            )
        return self._manage_stock_use_case
        
    @property
    def receive_use_case(self) -> ReceivingUseCase:
        if not self._receiving_use_case:
            self._receiving_use_case = ReceivingUseCase(
                repository=self.product_repository
            )
        return self._receiving_use_case

    @property
    def existing_stock_onboarding_use_case(
        self,
    ) -> ExistingStockOnboardingUseCase:
        if not self._existing_stock_onboarding_use_case:
            self._existing_stock_onboarding_use_case = (
                ExistingStockOnboardingUseCase(
                    repository=self.product_repository,
                    identity_provider=self.identity_provider,
                )
            )

        return self._existing_stock_onboarding_use_case

    @property
    def product_query_use_case(self) -> ProductQueryUseCase:
        if not self._product_query_use_case:
            self._product_query_use_case = ProductQueryUseCase(
                repository=self.product_repository
            )
        return self._product_query_use_case

    @property
    def product_suggestion_use_case(self) -> ProductSuggestionUseCase:
        if not self._product_suggestion_use_case:
            self._product_suggestion_use_case = ProductSuggestionUseCase(
                repository=self.product_repository
            )
        return self._product_suggestion_use_case

    @property
    def auth_use_case(self) -> ManageOperatorsUseCase:
        if not self._manage_operators_use_case:
            self._manage_operators_use_case = ManageOperatorsUseCase(
                repository=self.operator_repository, logger=self.logger
            )
        return self._manage_operators_use_case
    @property
    def category_use_case(self) -> ManageCategoriesUseCase:
        if not self._manage_categories_use_case:
            self._manage_categories_use_case = ManageCategoriesUseCase(
                repository=self.product_repository, logger=self.logger, identity_provider=self.identity_provider
            )
        return self._manage_categories_use_case
    @property
    def repository(self) -> SQLiteProductRepository:
        return self.product_repository

    @property
    def invoice_preparation(self) -> InvoicePreparationService:
        if self._invoice_preparation is None:
            self._invoice_preparation = InvoicePreparationService()

        return self._invoice_preparation

    @property
    def invoice_reconciliation(self) -> CatalogReconciliationService:
        if self._invoice_reconciliation is None:
            self._invoice_reconciliation = CatalogReconciliationService(
                catalog_repository=self.product_repository,
            )

        return self._invoice_reconciliation

    @property
    def unresolved_product(self) -> UnresolvedProductWorkflowService:
        if self._unresolved_product is None:
            self._unresolved_product = UnresolvedProductWorkflowService()

        return self._unresolved_product

    @property
    def product_onboarding(self) -> HumanProductOnboardingOrchestrator:
        if self._product_onboarding is None:
            self._product_onboarding = HumanProductOnboardingOrchestrator(
                repository=self.product_repository,
            )

        return self._product_onboarding

    @property
    def post_onboarding(self) -> PostOnboardingRereconciliationService:
        if self._post_onboarding is None:
            self._post_onboarding = PostOnboardingRereconciliationService(
                reconciliation_service=self.invoice_reconciliation,
            )

        return self._post_onboarding

