import os
from datetime import datetime
from src.interfaces.logger import Logger
class FileLogger(Logger):
    """
    Adapter concreto para gravação de logs institucionais.
    Garante inicialização segura do Storage e do próprio arquivo físico.
    """
    def __init__(self, file_path: str = "reports/logs/app.log"):
        self.file_path = file_path
        
        # GARANTIA DE INFRA INITIALIZATION E FS CONTRACT
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        # Cria fisicamente o arquivo vazio se não existir para satisfazer testes restritos
        if not os.path.exists(self.file_path):
            open(self.file_path, "a", encoding="utf-8").close()
    def _write(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} | {level} | {message}\n")
                f.flush()
        except Exception as e:
            print(f"CRITICAL [OBSERVABILITY LAYER]: Falha no contrato de IO - {str(e)}")
    def info(self, message: str) -> None:
        self._write("INFO", message)
    def warning(self, message: str) -> None:
        self._write("WARNING", message)
    def error(self, message: str) -> None:
        self._write("ERROR", message)
