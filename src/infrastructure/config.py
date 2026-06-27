import os

class Config:
    """
    Resolution Layer para configurações de ambiente.
    Remove todos os hardcodes da plataforma e centraliza a injeção.
    """
    def __init__(self):
        # Ambiente (development, testing, production)
        self.ENV = os.environ.get("KIPPE_ENV", "development")
        
        # Persistência
        self.DB_PATH = os.environ.get("KIPPE_DB_PATH", "data/estoque_producao.db")
        
        # Observabilidade
        self.LOG_PATH = os.environ.get("KIPPE_LOG_PATH", "reports/logs/app.log")
        
        # Rede / Bind
        self.HOST = os.environ.get("KIPPE_HOST", "0.0.0.0")
        self.PORT = int(os.environ.get("KIPPE_PORT", 5000))

    @classmethod
    def for_testing(cls):
        """Factory para forçar ambiente de teste de forma estrita."""
        os.environ["KIPPE_ENV"] = "testing"
        os.environ["KIPPE_DB_PATH"] = "data/test_strict.db"
        os.environ["KIPPE_LOG_PATH"] = "data/test_strict.log"
        return cls()
