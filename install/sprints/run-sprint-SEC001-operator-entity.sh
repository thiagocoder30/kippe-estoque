#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM B: IDENTITY & SECURITY
# SPRINT SEC001
# OPERATOR ENTITY & IDENTITY REPOSITORY
# ============================================================

set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${ROOT}"

export KIPPE_ROOT="${ROOT}"
export KIPPE_LOG_DIR="${ROOT}/reports/logs"

source install/lib/bootstrap.sh
source install/lib/testing.sh

kippe::init
kippe::init_environment

trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=7

kippe::banner_program \
    "B" \
    "SEC001" \
    "Operator Entity & Identity Repository"

kippe::step 1 ${TOTAL_STEPS} "Defining Operator Entity (Core Domain)..."
cat << 'EOF' > "${KIPPE_ROOT}/src/domain/operator.py"
from dataclasses import dataclass
from werkzeug.security import generate_password_hash, check_password_hash
from src.domain.result import Result

@dataclass
class Operator:
    id: str
    name: str
    pin_hash: str
    role: str = "OPERADOR"

    def verify_pin(self, pin: str) -> bool:
        """Verifica o PIN em tempo constante contra o hash criptográfico."""
        return check_password_hash(self.pin_hash, str(pin))

    @classmethod
    def create(cls, id: str, name: str, pin: str, role: str = "OPERADOR") -> Result['Operator', str]:
        """Factory method blindada com regras de segurança na criação."""
        if len(str(pin)) < 4 or not str(pin).isdigit():
            return Result.fail("O PIN deve conter no mínimo 4 dígitos numéricos.")
        
        if role not in ["OPERADOR", "GERENTE"]:
            return Result.fail(f"Role de segurança [{role}] inválida.")
        
        # Algoritmo seguro com salt aleatório embutido
        hashed_pin = generate_password_hash(str(pin))
        return Result.ok(cls(id=id, name=name, pin_hash=hashed_pin, role=role))
EOF

kippe::step 2 ${TOTAL_STEPS} "Creating SQLite Operator Repository (Persistence)..."
cat << 'EOF' > "${KIPPE_ROOT}/src/interfaces/sqlite_operator_repository.py"
import sqlite3
from typing import Optional
from src.domain.operator import Operator

class SQLiteOperatorRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS operators (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    pin_hash TEXT NOT NULL,
                    role TEXT NOT NULL
                )
            ''')
            conn.commit()

    def save(self, operator: Operator) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO operators (id, name, pin_hash, role) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET 
                    name=excluded.name, 
                    pin_hash=excluded.pin_hash,
                    role=excluded.role
            ''', (operator.id, operator.name, operator.pin_hash, operator.role))
            conn.commit()

    def get_by_id(self, operator_id: str) -> Optional[Operator]:
        with self._get_connection() as conn:
            row = conn.execute('SELECT * FROM operators WHERE id = ?', (operator_id,)).fetchone()
            if row:
                return Operator(
                    id=row['id'], 
                    name=row['name'], 
                    pin_hash=row['pin_hash'], 
                    role=row['role']
                )
            return None
EOF

kippe::step 3 ${TOTAL_STEPS} "Implementing ManageOperators Use Case..."
cat << 'EOF' > "${KIPPE_ROOT}/src/use_cases/manage_operators.py"
from typing import Optional
from src.domain.operator import Operator
from src.domain.result import Result
from src.interfaces.logger import Logger

class ManageOperatorsUseCase:
    def __init__(self, repository, logger: Optional[Logger] = None):
        self.repository = repository
        self.logger = logger

    def _log_info(self, msg: str):
        if self.logger: self.logger.info(msg)
        
    def _log_warn(self, msg: str):
        if self.logger: self.logger.warning(msg)

    def register(self, id: str, name: str, pin: str, role: str = "OPERADOR") -> Result[None, str]:
        if self.repository.get_by_id(id):
            self._log_warn(f"Segurança: Tentativa de sobrescrita de cadastro do Operador [{id}]")
            return Result.fail("Operador já cadastrado no sistema.")
        
        res = Operator.create(id=id, name=name, pin=pin, role=role)
        if res.is_success:
            self.repository.save(res.value)
            self._log_info(f"Governança: Novo Operador registrado [{id}] - {name} ({role})")
            return Result.ok(None)
        
        return Result.fail(res.error)

    def authenticate(self, id: str, pin: str) -> Result[Operator, str]:
        operator = self.repository.get_by_id(id)
        if not operator:
            self._log_warn(f"Auth: Falha de login (Operador não encontrado) [{id}]")
            return Result.fail("Credenciais inválidas.")
        
        if operator.verify_pin(pin):
            self._log_info(f"Auth: Operador autenticado com sucesso [{id}]")
            return Result.ok(operator)
        
        self._log_warn(f"Auth: Falha de login (PIN incorreto) para o Operador [{id}]")
        return Result.fail("Credenciais inválidas.")
EOF

kippe::step 4 ${TOTAL_STEPS} "Updating IoC Container to inject Identity Repositories..."
cat << 'EOF' > "${KIPPE_ROOT}/src/infrastructure/container.py"
from src.infrastructure.config import Config
from src.infrastructure.logger_adapter import FileLogger
from src.interfaces.sqlite_repository import SQLiteProductRepository
from src.interfaces.sqlite_operator_repository import SQLiteOperatorRepository
from src.use_cases.manage_stock import ManageStockUseCase
from src.use_cases.manage_operators import ManageOperatorsUseCase

class Container:
    """
    IoC Container Institucional.
    Centraliza a injeção de dependências do Programa A (Foundation) e B (Security).
    """
    def __init__(self, config_override: Config = None):
        self.config = config_override or Config()
        self._logger = None
        
        self._product_repository = None
        self._operator_repository = None
        
        self._manage_stock_use_case = None
        self._manage_operators_use_case = None

    @property
    def logger(self) -> FileLogger:
        if not self._logger:
            self._logger = FileLogger(self.config.LOG_PATH)
        return self._logger

    @property
    def product_repository(self) -> SQLiteProductRepository:
        if not self._product_repository:
            self._product_repository = SQLiteProductRepository(self.config.DB_PATH)
        return self._product_repository

    @property
    def operator_repository(self) -> SQLiteOperatorRepository:
        if not self._operator_repository:
            self._operator_repository = SQLiteOperatorRepository(self.config.DB_PATH)
        return self._operator_repository

    @property
    def use_case(self) -> ManageStockUseCase:
        """Alias para retrocompatibilidade com testes antigos do Core de Estoque."""
        if not self._manage_stock_use_case:
            self._manage_stock_use_case = ManageStockUseCase(
                repository=self.product_repository,
                logger=self.logger
            )
        return self._manage_stock_use_case
        
    @property
    def auth_use_case(self) -> ManageOperatorsUseCase:
        if not self._manage_operators_use_case:
            self._manage_operators_use_case = ManageOperatorsUseCase(
                repository=self.operator_repository,
                logger=self.logger
            )
        return self._manage_operators_use_case
EOF

kippe::step 5 ${TOTAL_STEPS} "Writing Strict Identity & Security Tests..."
cat << 'EOF' > "${KIPPE_ROOT}/tests/test_operator.py"
import pytest
import os
from src.infrastructure.config import Config
from src.infrastructure.container import Container

@pytest.fixture
def container():
    cfg = Config.for_testing()
    c = Container(cfg)
    # Garante banco limpo para o escopo de teste de segurança
    c.operator_repository._init_db()
    with c.operator_repository._get_connection() as conn:
        conn.execute('DELETE FROM operators')
        conn.commit()
    
    yield c
    
    if os.path.exists(cfg.DB_PATH): os.remove(cfg.DB_PATH)
    if os.path.exists(cfg.LOG_PATH): os.remove(cfg.LOG_PATH)

def test_operator_pin_is_hashed_and_verified(container):
    auth_uc = container.auth_use_case
    
    # 1. Registro
    res_reg = auth_uc.register("1045", "João Silva", "1234", "OPERADOR")
    assert res_reg.is_success is True
    
    # Validação estrutural de que o banco não salvou '1234'
    operator_raw = container.operator_repository.get_by_id("1045")
    assert operator_raw.pin_hash != "1234"
    assert len(operator_raw.pin_hash) > 20 # Hash do werkzeug é grande
    
    # 2. Autenticação Correta
    res_auth = auth_uc.authenticate("1045", "1234")
    assert res_auth.is_success is True
    assert res_auth.value.name == "João Silva"
    
    # 3. Falha de Autenticação
    res_fail = auth_uc.authenticate("1045", "0000")
    assert res_fail.is_success is False
    assert "Credenciais inválidas" in res_fail.error

def test_operator_creation_validation(container):
    auth_uc = container.auth_use_case
    
    # PIN curto
    res = auth_uc.register("999", "Admin", "12")
    assert res.is_success is False
    
    # Role inválida
    res2 = auth_uc.register("888", "Hacker", "1234", "SUPERUSER")
    assert res2.is_success is False
EOF

kippe::step 6 ${TOTAL_STEPS} "Validating Security Layer in Sandbox..."
# O orquestrador vai garantir que todos os novos testes de criptografia passem
kippe::test_execute_all

kippe::step 7 ${TOTAL_STEPS} "Updating Governance and Committing..."
cat << 'EOF' > ESTADO_PROJETO.md
# 🌐 KIPPE PLATFORM: Institutional Retail Operations

## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 2 (Profissional).

## 2. Status Executivo
* **Programa Atual:** PROGRAMA B (Identity & Security)
* **Gate Alvo:** GATE B - Security Ready
* **Última Entrega:** Sprint SEC001 (Operator Entity & Identity Repository)

## 3. Diretórios e Artefatos Essenciais
* `data/` - (Fronteira de persistência SQLite)
* `docs/architecture/` - (Manifesto e ADRs)
* `src/domain/operator.py` - (Entidade blindada com criptografia de PIN)
* `src/infrastructure/container.py` - (IoC com Identity Services injetados)

## 4. Próxima Ação Requerida
* **Sprint SEC002 (AuthN & Session Middleware):** Agora que o sistema sabe criar e persistir operadores de forma criptografada, precisamos de um mecanismo na API (Flask) que proteja as rotas. Implementaremos um middleware de sessão baseado em tokens efêmeros JWT (JSON Web Tokens) para manter a sessão aberta no dispositivo da loja sem gerar fricção.
EOF

kippe::checkpoint_create \
    "008" \
    "1.0.0" \
    "SEC001" \
    "SUCCESS"

kippe::manifest_create \
    "SEC001" \
    "B" \
    "1.0.0" \
    "SUCCESS" \
    "SEC002"

git add src/domain/operator.py src/interfaces/sqlite_operator_repository.py src/use_cases/manage_operators.py src/infrastructure/container.py tests/test_operator.py ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_SEC001.json
git commit -m "feat(security): implementa entidade Operator com hashing criptografico e repositorio SQLite (SEC001)" || true

kippe::banner_finish
kippe::success "Operator Entity successfully established."
echo -e "\nNext Sprint: SEC002 (AuthN & Session Middleware)\n"

