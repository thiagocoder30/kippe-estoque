#!/bin/bash
# Kippe-Estoque Core | Sprint 001: Fundação Clean Architecture & Domínio

# 1. Instalação de dependências estritas
pip install pytest

# 2. Estruturação Modular de Diretórios (Clean Architecture)
mkdir -p src/domain src/use_cases src/interfaces tests
touch src/__init__.py src/domain/__init__.py src/use_cases/__init__.py src/interfaces/__init__.py tests/__init__.py

# 3. Padrão Result para Tratamento de Erros Profissional
cat << 'EOF' > src/domain/result.py
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
EOF

# 4. Entidade de Domínio Puro e Tipagem Estrita
cat << 'EOF' > src/domain/product.py
from dataclasses import dataclass
from .result import Result

@dataclass
class Product:
    """
    Entidade Central (Core Domain). 
    Operações Idempotentes e Complexidade de Tempo O(1).
    """
    id: str
    name: str
    quantity: int

    def add_stock(self, amount: int) -> Result[None, str]:
        if amount <= 0:
            return Result.fail("Violação de Regra: A quantidade de entrada deve ser > 0.")
        self.quantity += amount
        return Result.ok(None)

    def remove_stock(self, amount: int) -> Result[None, str]:
        if amount <= 0:
            return Result.fail("Violação de Regra: A quantidade de saída deve ser > 0.")
        if self.quantity < amount:
            return Result.fail("Violação de Regra: Estoque insuficiente para a transação.")
        self.quantity -= amount
        return Result.ok(None)
EOF

# 5. Suíte de Testes Unitários de Baixa Latência
cat << 'EOF' > tests/test_domain.py
from src.domain.product import Product

def test_add_stock_success():
    p = Product(id="KPC-100", name="Arroz 5kg", quantity=20)
    res = p.add_stock(5)
    assert res.is_success is True
    assert p.quantity == 25

def test_add_stock_fail_negative():
    p = Product(id="KPC-100", name="Arroz 5kg", quantity=20)
    res = p.add_stock(-2)
    assert res.is_success is False
    assert res.error == "Violação de Regra: A quantidade de entrada deve ser > 0."

def test_remove_stock_success():
    p = Product(id="KPC-100", name="Arroz 5kg", quantity=20)
    res = p.remove_stock(10)
    assert res.is_success is True
    assert p.quantity == 10

def test_remove_stock_fail_insufficient():
    p = Product(id="KPC-100", name="Arroz 5kg", quantity=20)
    res = p.remove_stock(50)
    assert res.is_success is False
    assert p.quantity == 20
    assert res.error == "Violação de Regra: Estoque insuficiente para a transação."
EOF

# 6. Execução automatizada e Verificação do Core
echo -e "\n[!] Iniciando Validação do Kippe-Estoque Core...\n"
python -m pytest tests/ -v

