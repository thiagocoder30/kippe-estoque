from src.infrastructure.config import Config
from src.infrastructure.logger_adapter import FileLogger
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.use_cases.manage_stock import ManageStockUseCase

class Container:
    """
    IoC Container Institucional.
    Gerencia o ciclo de vida e resolve dependências em cascata com Lazy Loading.
    """
    def __init__(self, config_override: Config = None):
        self.config = config_override or Config()
        self._logger = None
        self._repository = None
        self._use_case = None

    @property
    def logger(self) -> FileLogger:
        if not self._logger:
            self._logger = FileLogger(self.config.LOG_PATH)
        return self._logger

    @property
    def repository(self) -> SQLiteProductRepository:
        if not self._repository:
            self._repository = SQLiteProductRepository(self.config.DB_PATH)
        return self._repository

    @property
    def use_case(self) -> ManageStockUseCase:
        if not self._use_case:
            self._use_case = ManageStockUseCase(
                repository=self.repository,
                logger=self.logger
            )
        return self._use_case
