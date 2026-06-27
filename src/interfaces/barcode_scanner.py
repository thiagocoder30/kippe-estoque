from typing import Protocol
from src.domain.result import Result

class BarcodeScanner(Protocol):
    """
    Interface para leitores de código de barras.
    Protege o sistema Core de implementações de hardware específicas.
    """
    def scan(self) -> Result[str, str]:
        ...
