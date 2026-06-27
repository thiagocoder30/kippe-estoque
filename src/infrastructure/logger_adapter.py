import os
from datetime import datetime
from src.interfaces.logger import Logger

class FileLogger:
    """
    Adapter concreto para gravação de logs institucionais.
    Garante o contrato de FileSystem (FS) com inicialização de Storage
    escrita determinística e flush imediato.
    """
    def __init__(self, file_path: str = "reports/logs/app.log"):
        self.file_path = file_path
        
        # GARANTIA DE INFRA INITIALIZATION
        # Assegura que o storage layer existe antes de qualquer tentativa de I/O
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def _write(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # GARANTIA DE SIDE-EFFECT
        # Abertura em modo append, escrita explícita e flush imediato no disco
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} | {level} | {message}\n")
                f.flush()
        except Exception as e:
            # Fallback de segurança para não derrubar o Core se houver falha de hardware/permissão
            print(f"CRITICAL [OBSERVABILITY LAYER]: Falha no contrato de IO - {str(e)}")

    def info(self, message: str) -> None:
        self._write("INFO", message)

    def warning(self, message: str) -> None:
        self._write("WARNING", message)

    def error(self, message: str) -> None:
        self._write("ERROR", message)
