from typing import TypeVar, Generic, Optional

T = TypeVar('T')
E = TypeVar('E')

class Result(Generic[T, E]):
    """
    Padrão Result (Either) para evitar Exceptions silenciosas.
    Garante gestão de memória otimizada e previsibilidade das operações.
    """
    def __init__(self, is_success: bool, value: Optional[T], error: Optional[E]):
        self.is_success = is_success
        self.value = value
        self.error = error

    @staticmethod
    def ok(value: T) -> 'Result[T, E]':
        return Result(True, value, None)

    @staticmethod
    def fail(error: E) -> 'Result[T, E]':
        return Result(False, None, error)
