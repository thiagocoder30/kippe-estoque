from typing import Protocol

class Logger(Protocol):
    """
    Contrato de Observabilidade.
    Garante que as regras de negócio desconheçam a biblioteca de logging utilizada.
    """
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
