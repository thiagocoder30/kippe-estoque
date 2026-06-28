#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A: FOUNDATION
# SPRINT A003.2 (HOTFIX ARCHITECTURE)
# OBSERVABILITY FS CONTRACT & STORAGE INITIALIZATION
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
    "A003.2" \
    "Observability FS Contract"

kippe::step 1 ${TOTAL_STEPS} "Refactoring FileLogger for Deterministic FS Contract..."
cat << 'EOF' > "${KIPPE_ROOT}/src/infrastructure/logger_adapter.py"
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
EOF

kippe::step 2 ${TOTAL_STEPS} "Re-Validating Architecture Integrity..."
kippe::test_execute_all

kippe::step 3 ${TOTAL_STEPS} "Updating Governance and Committing..."
cat << 'EOF' > ESTADO_PROJETO.md
# 🌐 KIPPE PLATFORM: Institutional Retail Operations

## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 1 (Funcional).

## 2. Status Executivo
* **Programa Atual:** PROGRAMA A (Foundation)
* **Gate Alvo:** GATE A - Foundation Ready
* **Última Entrega:** Sprint A003.2 (Observability FS Contract)

## 3. Diretórios e Artefatos Essenciais
* `data/` - (Fronteira de persistência SQLite local)
* `docs/architecture/MANIFESTO.md` - (Constituição do Sistema)
* `install/sprints/` - (Motor CI arquivado e ativo)
* `reports/logs/app.log` - (Log Institucional com Contrato FS Determinístico)

## 4. Próxima Ação Requerida
* **Sprint A004 (Configuration & Environments):** Desacoplar caminhos absolutos e configurações mágicas injetando uma camada de resolução de ambiente (`.env`), finalizando os requisitos de infraestrutura base.
EOF

kippe::checkpoint_create \
    "004" \
    "1.0.0" \
    "A003.2" \
    "SUCCESS"

kippe::manifest_create \
    "A003.2" \
    "A" \
    "1.0.0" \
    "SUCCESS" \
    "A004"

kippe::step 4 ${TOTAL_STEPS} "Committing Fixes..."
git add src/infrastructure/logger_adapter.py ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_A003.2.json
git commit -m "fix(observability): implementa contrato FS deterministico e inicializacao segura de storage" || true

kippe::banner_finish
kippe::success "Observability FS Contract established and verified."
echo -e "\nNext Sprint: A004 (Configuration & Environments)\n"

