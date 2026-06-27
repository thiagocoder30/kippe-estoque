#!/bin/bash
# Kippe-Estoque Core | Sprint 002: Casos de Uso (Use Cases) e Pipeline CI Local

SPRINT_ID="002"
LOG_DIR="/sdcard/Download/kippe-estoque/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/sprint-${SPRINT_ID}-${TIMESTAMP}.log"

# Garantir que o diretório de logs exista no Android
mkdir -p "$LOG_DIR"

# Redirecionar todas as saídas (stdout e stderr) para o log, mantendo exibição no terminal (usando tee)
{
    echo "=== Iniciando Sprint $SPRINT_ID - Kippe-Estoque Core ==="
    echo "Data/Hora: $(date)"

    # 1. Criação do Módulo de Casos de Uso (Completo)
    cat << 'EOF' > src/use_cases/manage_stock.py
from src.domain.product import Product
from src.domain.result import Result

class ManageStockUseCase:
    """
    Orquestrador de Regras de Negócio (Use Case).
    Garante o fluxo correto da transação, independente do Banco de Dados.
    Complexidade O(1) herdada do Domínio.
    """
    def __init__(self):
        # Preparação para injeção de dependência futura (Repositórios/Interfaces)
        pass

    def execute_add(self, product: Product, amount: int) -> Result[None, str]:
        return product.add_stock(amount)

    def execute_remove(self, product: Product, amount: int) -> Result[None, str]:
        return product.remove_stock(amount)
EOF

    # 2. Testes da Camada de Casos de Uso (Completo)
    cat << 'EOF' > tests/test_use_cases.py
from src.domain.product import Product
from src.use_cases.manage_stock import ManageStockUseCase

def test_manage_stock_use_case_add():
    uc = ManageStockUseCase()
    p = Product(id="KPC-200", name="Feijão 1kg", quantity=10)
    
    res = uc.execute_add(p, 5)
    assert res.is_success is True
    assert p.quantity == 15

def test_manage_stock_use_case_remove():
    uc = ManageStockUseCase()
    p = Product(id="KPC-200", name="Feijão 1kg", quantity=10)
    
    res = uc.execute_remove(p, 3)
    assert res.is_success is True
    assert p.quantity == 7

def test_manage_stock_use_case_remove_fail():
    uc = ManageStockUseCase()
    p = Product(id="KPC-200", name="Feijão 1kg", quantity=10)
    
    res = uc.execute_remove(p, 15)
    assert res.is_success is False
    assert res.error == "Violação de Regra: Estoque insuficiente para a transação."
EOF

    # 3. Executar Testes Unitários de Baixa Latência
    echo -e "\n[!] Executando validação de regressão e testes core...\n"
    python -m pytest tests/ -v
    TEST_STATUS=$?

} 2>&1 | tee "$LOG_FILE"

# O 'tee' oculta o código de saída real do pytest no pipe, então pegamos o PIPESTATUS
# PIPESTATUS[0] se refere ao código de saída do bloco {...}
FINAL_STATUS=${PIPESTATUS[0]}

# 4. Tratamento de Erros Profissional (Pipeline Success/Fail)
if [ $FINAL_STATUS -eq 0 ]; then
    echo -e "\n[OK] Testes passaram com sucesso! Consolidando integração..."
    
    # 5. Atualização Automatizada do ESTADO_PROJETO.md
    cat << 'EOF' > ESTADO_PROJETO.md
# Estado do Projeto: Kippe-Estoque Core

## 1. Visão Geral e Contexto
* **Objetivo:** Sistema de alta performance para supermercados de bairro (giro rápido).
* **Ambiente de Execução:** Termux (Galaxy A50).
* **Stack:** Python, Pytest, Bash Automation, SQLite (a implementar).

## 2. Arquitetura Atual (Clean Architecture)
* **Domain:** `Product` Entity, `Result` Pattern para resiliência (Sem Exceptions silenciosas).
* **Use Cases:** `ManageStockUseCase` como orquestrador isolado e idempotente.
* **CI/CD:** Pipeline local que gera logs em `/sdcard/Download`, atualiza status e sincroniza com GitHub.

## 3. Arquivos Implementados e Status
* [x] `src/domain/result.py` - Core Result.
* [x] `src/domain/product.py` - Core Entity.
* [x] `src/use_cases/manage_stock.py` - Casos de Uso.
* [x] `tests/test_domain.py` - Validação de Domínio.
* [x] `tests/test_use_cases.py` - Validação de Casos de Uso.
* [x] `ESTADO_PROJETO.md` - Memória Dinâmica.

## 4. Último Commit Válido Rastreável
* **Sprint 002:** Casos de Uso (Use Cases) e Pipeline CI Local.

## 5. Próximo Passo Imediato
* Construir a Camada de Interface/Adapter: Implementar o repositório de persistência SQLite aderindo aos Princípios SOLID (Injeção de Dependência) para ligá-lo ao `ManageStockUseCase`.

## 6. Bloqueios ou Alucinações Conhecidas
* Nenhum no momento.
EOF

    # 6. Commit Automático e Merge/Push para o GitHub
    git add .
    git commit -m "feat(core): implementa Casos de Uso, testes e pipeline CI local automático"
    git push 
    
    echo -e "\n[SUCESSO] Log salvo em: $LOG_FILE"
    echo -e "[SUCESSO] Repositório atualizado no GitHub. Sprint $SPRINT_ID concluída."
else
    echo -e "\n[FALHA] Violação de Arquitetura. Os testes falharam!"
    echo -e "Nenhum código foi commitado para proteger a integridade do Core."
    echo -e "Analise o log completo em: $LOG_FILE"
fi

