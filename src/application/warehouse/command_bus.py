from typing import Type, Dict, Any

class CommandBus:
    """
    Orquestrador central de Comandos.
    Desacopla a emissão do comando da sua execução física,
    garantindo que cada intenção tenha um único Handler responsável.
    """
    def __init__(self):
        self._handlers: Dict[Type, Any] = {}

    def register(self, command_type: Type, handler: Any) -> None:
        self._handlers[command_type] = handler

    def dispatch(self, command: Any) -> None:
        handler = self._handlers.get(type(command))
        if not handler:
            raise ValueError(f"Nenhum handler registado para o comando: {type(command).__name__}")
        handler.execute(command)
