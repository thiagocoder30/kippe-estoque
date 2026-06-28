#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A: FOUNDATION
# SPRINT A005.1 (HOTFIX ARCHITECTURE)
# IOC CONTAINER COMPATIBILITY LAYER
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

TOTAL_STEPS=4

kippe::banner_program \
    "A" \
    "A005.1" \
    "IoC Compatibility Layer"

kippe::step 1 ${TOTAL_STEPS} "Refactoring Container with Backward Compatibility Bindings..."
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
    Gerencia o ciclo de vida e resolve dependências do Programa A e B.
    Inclui uma Compatibility Layer para evitar regressões estruturais no legado.
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

    # ========================================================
    # COMPATIBILITY LAYER (BACKWARD COMPATIBILITY BINDINGS)
    # Evita a quebra de testes legados e contratos antigos da API
    # ========================================================
    @property
    def repository(self) -> SQLiteProductRepository:
        """Alias retrocompatível para o repositório de produtos."""
        return self.product_repository
EOF

kippe::step 2 ${TOTAL_STEPS} "Re-Running Complete Test Suite (Validation)..."
# Invocando o pipeline. Ele irá rodar TODOS os 17 testes (A e B juntos)
kippe::test_execute_all

kippe::step 3 ${TOTAL_STEPS} "Updating System Executive State..."
cat << 'EOF' > ESTADO_PROJETO.md
# 🌐 KIPPE PLATFORM: Institutional Retail Operations

## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 2 (Profissional).

## 2. Status Executivo
* **Programa Atual:** PROGRAMA B (Identity & Security)
* **Gate Transposto:** [ GATE A - FOUNDATION READY ] ✅ (Estabilizado pós-compatibilidade)
* **Última Entrega:** Sprint A005.1 (IoC Container Compatibility Layer)

## 3. Diretórios e Artefatos Essenciais
* `data/` - (Fronteira de persistência SQLite)
* `docs/architecture/` - (Manifesto, ADR-001 e Modelos de Confiança)
* `src/infrastructure/container.py` - (IoC Container com Compatibility Layer Ativa)
* `reports/logs/` - (Logs de infraestrutura e aplicação unificados)

## 4. Próxima Ação Requerida
* **Sprint SEC002 (AuthN & Session Middleware):** Com o contêiner estabilizado e tolerante a múltiplas gerações de código, podemos prosseguir com segurança para a proteção das rotas HTTP no Flask, estabelecendo o ciclo de vida das sessões dos operadores através de tokens efêmeros.
EOF

kippe::checkpoint_create \
    "009" \
    "1.0.0" \
    "A005.1" \
    "SUCCESS"

kippe::manifest_create \
    "A005.1" \
    "A" \
    "1.0.0" \
    "SUCCESS" \
    "SEC002"

kippe::step 4 ${TOTAL_STEPS} "Committing Stabilization Patch..."
git add src/infrastructure/container.py ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_A005.1.json
git commit -m "fix(infra): adiciona compatibility alias no container IoC para suportar fixtures legadas (A005.1)" || true

kippe::banner_finish
kippe::success "Container Compatibility Patch successfully integrated."
echo -e "\nNext Sprint: SEC002 (AuthN & Session Middleware)\n"
EOF

