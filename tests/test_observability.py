import os
import pytest
from src.infrastructure.logger_adapter import FileLogger
from src.use_cases.manage_stock import ManageStockUseCase
from src.interfaces.sqlite_repository import SQLiteProductRepository

def test_logger_writes_to_file():
    log_file = "data/test_app.log"
    if os.path.exists(log_file): os.remove(log_file)
    
    logger = FileLogger(log_file)
    logger.info("Test Info Message")
    logger.warning("Test Warning Message")
    
    assert os.path.exists(log_file)
    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Test Info Message" in content
        assert "Test Warning Message" in content
        
    if os.path.exists(log_file): os.remove(log_file)
    
def test_use_case_logging_integration():
    db = "data/test_obs.db"
    log = "data/test_obs.log"
    repo = SQLiteProductRepository(db)
    logger = FileLogger(log)
    uc = ManageStockUseCase(repo, logger)
    
    # Aciona uma regra de negócio que deve ser barrada e logada
    uc.execute_add("SKU-FANTASMA", 10, "2030-12-31", "L01")
    
    with open(log, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Entrada Bloqueada: SKU [SKU-FANTASMA]" in content
        
    if os.path.exists(db): os.remove(db)
    if os.path.exists(log): os.remove(log)
