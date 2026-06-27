from src.infrastructure.config import Config
from src.infrastructure.logger_adapter import FileLogger
from src.infrastructure.identity import CurrentOperatorResolver
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.interfaces.sqlite_operator_repository import SQLiteOperatorRepository
from src.use_cases.manage_stock import ManageStockUseCase
from src.use_cases.manage_operators import ManageOperatorsUseCase
from src.use_cases.manage_categories import ManageCategoriesUseCase
class Container:
    def __init__(self, config_override: Config = None):
        self.config = config_override or Config()
        self._logger = None
        self._identity_provider = None
        self._product_repository = None
        self._operator_repository = None
        self._manage_stock_use_case = None
        self._manage_operators_use_case = None
        self._manage_categories_use_case = None
    @property
    def logger(self) -> FileLogger:
        if not self._logger: self._logger = FileLogger(self.config.LOG_PATH)
        return self._logger
    @property
    def identity_provider(self) -> CurrentOperatorResolver:
        if not self._identity_provider: self._identity_provider = CurrentOperatorResolver(self.config.ENV)
        return self._identity_provider
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
