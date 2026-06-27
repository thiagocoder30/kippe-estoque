import os
from src.infrastructure.config import Config

def test_config_default_resolution():
    if "KIPPE_ENV" in os.environ: del os.environ["KIPPE_ENV"]
    cfg = Config()
    assert cfg.ENV == "development"
    assert cfg.PORT == 5000

def test_config_strict_testing_factory():
    cfg = Config.for_testing()
    assert cfg.ENV == "testing"
    assert "test_strict.db" in cfg.DB_PATH
