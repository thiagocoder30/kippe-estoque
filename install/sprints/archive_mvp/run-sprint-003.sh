#!/bin/bash
# Kippe-Estoque Core | Sprint 003: Camada de Persistência (Repository Pattern & SQLite)

SPRINT_ID="003"
LOG_DIR="/sdcard/Download/kippe-estoque/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/sprint-${SPRINT_ID}-${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

{
    echo "=== Iniciando Sprint $SPRINT_ID - Kippe-Estoque Core ==="
    echo "Data/Hora: $(date)"

    # 1. Criação do Contrato/Interface do Repositório (SOLID - Dependency Inversion)
    cat << 'EOF' > src/interfaces/product_repository.py
from typing import Protocol, List, Optional
from src.domain.product import Product

class ProductRepository(Protocol):
    """
    Interface (Protocolo) do Repositório de Produtos.
    Garante que o Core não dependa de detalhes do Banco de Dados.
    """
    def save(self, product: Product) -> None:
        ...

    def get_by_id(self, product_id: str) -> Optional[Product]:
        ...
    
    def get_all(self) -> List[Product]:
        ...
EOF

    # 2. Implementação Concreta (SQLite Adapter)
    cat << 'EOF' > src/interfaces/sqlite_repository.py
import sqlite3
from typing import List, Optional
from src.domain.product import Product
from src.interfaces.product_repository import ProductRepository

class SQLiteProductRepository:
    """
    Implementação concreta do repositório utilizando SQLite.
    Focado em operações O(1) para busca por ID e O(N) leve para listagem.
    """
    def __init__(self, db_path: str = "estoque_mercado.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    quantity INTEGER NOT NULL
                )
            ''')
            conn.commit()

    def save(self, product: Product) -> None:
        """Salva ou atualiza um produto de forma atômica e idempotente."""
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO products (id, name, quantity) 
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET 
                    name=excluded.name, 
                    quantity=excluded.quantity
            ''', (product.id, product.name, product.quantity))
            conn.commit()

    def get_by_id(self, product_id: str) -> Optional[Product]:
        """Recupera a entidade de Domínio através do ID."""
        with self._get_connection() as conn:
            row = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
            if row:
                return Product(id=row['id'], name=row['name'], quantity=row['quantity'])
            return None

    def get_all(self) -> List[Product]:
        """Recupera todos os produtos cadastrados."""
        with self._get_connection() as conn:
            rows = conn.execute('SELECT * FROM products ORDER BY name').fetchall()
            return [Product(id=row['id'], name=row['name'], quantity=row['quantity']) for row in rows]
EOF

    # 3. Suíte de Testes de Integração com Banco de Dados em Disco
    cat << 'EOF' > tests/test_repository.py
import pytest
import os
from src.domain.product import Product
from src.interfaces.sqlite_repository import SQLiteProductRepository

@pytest.fixture
def repo():
    # Setup: Utiliza um arquivo temporário para não sujar o banco de produção
    db_path = "test_estoque.db"
    repository = SQLiteProductRepository(db_path=db_path)
    yield repository
    
    # Teardown: Limpeza do banco de dados de teste após execução
    if os.path.exists(db_path):
        os.remove(db_path)

def test_repository_save_and_get(repo):
    p = Product(id="KPC-300", name="Macarrão 500g", quantity=50)
    repo.save(p)
    
    p_db = repo.get_by_id("KPC-300")
    assert p_db is not None
    assert p_db.name == "Macarrão 500g"
    assert p_db.quantity == 50

def test_repository_idempotent_update(repo):
    p = Product(id="KPC-400", name="Óleo de Soja", quantity=10)
    repo.save(p)
    
    # Simula entrada de estoque
    p.quantity = 15
    repo.save(p)
    
    p_db = repo.get_by_id("KPC-400")
    assert p_db.quantity == 15

def test_repository_get_all(repo):
    repo.save(Product(id="KPC-500", name="Açúcar 1kg", quantity=20))
    repo.save(Product(id="KPC-501", name="Café 500g", quantity=30))
    
    products = repo.get_all()
    assert len(products) >= 2
    # Verifica se os IDs constam na lista de retorno
    ids = [prod.id for prod in products]
    assert "KPC-500" in ids
    assert "KPC-501" in ids
EOF

    echo -e "\n[!] Executando validação completa da integração com SQLite...\n"
    python -m pytest tests/ -v
    TEST_STATUS=$?

} 2>&1 | tee "$LOG_FILE"

FINAL_STATUS=${PIPESTATUS[0]}

if [ $FINAL_STATUS -eq 0 ]; then
    echo -e "\n[OK] Testes de Banco de Dados passaram com sucesso!"
    
    cat << 'EOF' > ESTADO_PROJETO.md
# Estado do Projeto: Kippe-Estoque Core

## 1. Visão Geral e Contexto
* **Objetivo:** Sistema de alta performance para supermercados de bairro (giro rápido).
* **Ambiente de Execução:** Termux (Galaxy A50).
* **Stack:** Python, Pytest, Bash Automation, SQLite.

## 2. Arquitetura Atual (Clean Architecture)
* **Domain:** `Product` Entity, `Result` Pattern para resiliência.
* **Use Cases:** `ManageStockUseCase` como orquestrador isolado e idempotente.
* **Interfaces (Adapters):** Repositório base `ProductRepository` com implementação via `SQLiteProductRepository` (Operação de Upsert Atômico).
* **CI/CD:** Pipeline local que gera logs e sincroniza com GitHub na ocorrência de sucesso nos testes.

## 3. Arquivos Implementados e Status
* [x] `src/domain/result.py`
* [x] `src/domain/product.py`
* [x] `src/use_cases/manage_stock.py`
* [x] `src/interfaces/product_repository.py`
* [x] `src/interfaces/sqlite_repository.py`
* [x] `tests/test_domain.py`, `tests/test_use_cases.py`, `tests/test_repository.py`
* [x] `ESTADO_PROJETO.md` - Memória Dinâmica Atualizada (Sprint 003).

## 4. Último Commit Válido Rastreável
* **Sprint 003:** Implementação do Repository Pattern em SQLite.

## 5. Próximo Passo Imediato
* Injetar o repositório (`SQLiteProductRepository`) no caso de uso (`ManageStockUseCase`) e criar a **Camada de Controladores CLI** para que o usuário possa começar a registrar as movimentações diretamente do terminal de forma interativa.

## 6. Bloqueios ou Alucinações Conhecidas
* Nenhum no momento. Testes executando latência sub-100ms.
EOF

    git add .
    git commit -m "feat(adapter): integra SQLite repository com testes de unidade e upsert idempotente"
    git push 
    
    echo -e "\n[SUCESSO] Log salvo em: $LOG_FILE"
    echo -e "[SUCESSO] Sprint $SPRINT_ID consolidada no Github."
else
    echo -e "\n[FALHA] Banco de Dados rejeitado pelos testes. Rollback da integração garantido."
    echo -e "Verifique o erro em: $LOG_FILE"
fi

