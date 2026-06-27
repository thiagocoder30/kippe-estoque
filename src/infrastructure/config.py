import os

class Config:
    """
    Resolution Layer para configurações de ambiente.
    Injeta chaves criptográficas para governança de sessões seguras.
    """
    def __init__(self):
        self.ENV = os.environ.get("KIPPE_ENV", "development")
        self.DB_PATH = os.environ.get("KIPPE_DB_PATH", "data/estoque_producao.db")
        self.LOG_PATH = os.environ.get("KIPPE_LOG_PATH", "reports/logs/app.log")
        self.HOST = os.environ.get("KIPPE_HOST", "0.0.0.0")
        self.PORT = int(os.environ.get("KIPPE_PORT", 5000))
        
        # 12-Factor Secret Management
        self.SECRET_KEY = os.environ.get("KIPPE_SECRET_KEY", "9xW_institutional_secure_fallback_core_key_#71")

    @classmethod
    def for_testing(cls):
        os.environ["KIPPE_ENV"] = "testing"
        os.environ["KIPPE_DB_PATH"] = "data/test_strict.db"
        os.environ["KIPPE_LOG_PATH"] = "data/test_strict.log"
        os.environ["KIPPE_SECRET_KEY"] = "test-crypto-key-signature"
        return cls()
