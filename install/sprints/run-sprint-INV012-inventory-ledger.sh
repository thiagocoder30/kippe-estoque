#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM C: INVENTORY
# SPRINT INV012: INVENTORY LEDGER (Livro-Razão Imutável)
# ============================================================
set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"
# 1. Bootstrap (13-Step Frozen Framework)
source install/lib/bootstrap.sh
source install/lib/testing.sh
source install/lib/validation.sh
kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR
TOTAL_STEPS=3
kippe::banner_program "C" "INV012" "Inventory Ledger"
# 2. Domain Evolution (SafeRefactor / Entity Injection)
kippe::step 1 ${TOTAL_STEPS} "Applying Domain Mutations: Immutable Ledger & Persistence..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/ledger.py"
from dataclasses import dataclass, field
from datetime import datetime
@dataclass(frozen=True)
class LedgerEntry:
    """
    Entidade: LedgerEntry (Livro-Razão Imutável)
    Garante a rastreabilidade cronológica e a integridade de todas as movimentações.
    A flag 'frozen=True' impede modificações retroativas em memória.
    """
    id: str
    product_id: str
    event_type: str  # IN, OUT, RESERVE, TRANSFER, ADJUST, COUNT
    quantity_change: int
    quantity_before: int
    quantity_after: int
    warehouse_id: str
    batch_code: str
    operator_id: str
    reference_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    def __post_init__(self):
        # Validações de Invariantes de Auditoria
        if not self.id:
            raise ValueError("O ID do registro é obrigatório.")
        if not self.operator_id:
            raise ValueError("A auditoria exige a identificação do operador (operator_id).")
        if self.event_type not in ["IN", "OUT", "RESERVE", "TRANSFER", "ADJUST", "COUNT"]:
            raise ValueError(f"Tipo de evento inválido: {self.event_type}")
        
        # Conservação da Invariante Matemática
        if self.quantity_before + self.quantity_change != self.quantity_after:
            raise ValueError(f"Invariante matemática violada: {self.quantity_before} + ({self.quantity_change}) != {self.quantity_after}.")
KIPPE_HUNK
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/interfaces/sqlite_ledger_repository.py"
import sqlite3
from typing import List
from src.domain.ledger import LedgerEntry
class SQLiteLedgerRepository:
    """
    Adapter: SQLiteLedgerRepository
    Isola a responsabilidade de escrita do Livro-Razão (Append-Only).
    """
    def __init__(self, db_path: str = "data/estoque_producao.db"):
        self.db_path = db_path
        self._init_db()
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS inventory_ledger (
                    id TEXT PRIMARY KEY, product_id TEXT NOT NULL, event_type TEXT NOT NULL,
                    quantity_change INTEGER NOT NULL, quantity_before INTEGER NOT NULL,
                    quantity_after INTEGER NOT NULL, warehouse_id TEXT NOT NULL,
                    batch_code TEXT NOT NULL, operator_id TEXT NOT NULL,
                    reference_id TEXT, timestamp DATETIME NOT NULL
                )
            ''')
            conn.commit()
    def append(self, entry: LedgerEntry) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO inventory_ledger (
                    id, product_id, event_type, quantity_change, quantity_before,
                    quantity_after, warehouse_id, batch_code, operator_id,
                    reference_id, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry.id, entry.product_id, entry.event_type, entry.quantity_change,
                entry.quantity_before, entry.quantity_after, entry.warehouse_id,
                entry.batch_code, entry.operator_id, entry.reference_id, entry.timestamp
            ))
            conn.commit()
    def get_history_by_product(self, product_id: str) -> List[LedgerEntry]:
        with self._get_connection() as conn:
            rows = conn.execute('SELECT * FROM inventory_ledger WHERE product_id = ? ORDER BY timestamp ASC, id ASC', (product_id,)).fetchall()
            return [LedgerEntry(
                id=dict(r)['id'], product_id=dict(r)['product_id'], event_type=dict(r)['event_type'],
                quantity_change=dict(r)['quantity_change'], quantity_before=dict(r)['quantity_before'],
                quantity_after=dict(r)['quantity_after'], warehouse_id=dict(r)['warehouse_id'],
                batch_code=dict(r)['batch_code'], operator_id=dict(r)['operator_id'],
                reference_id=dict(r)['reference_id'], timestamp=dict(r)['timestamp']
            ) for r in rows]
KIPPE_HUNK
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/test_inventory_ledger.py"
import pytest
from dataclasses import FrozenInstanceError
from src.domain.ledger import LedgerEntry
def test_ledger_entry_is_immutable():
    entry = LedgerEntry(
        id="TX-001", product_id="SKU-1", event_type="IN",
        quantity_change=10, quantity_before=0, quantity_after=10,
        warehouse_id="WH-1", batch_code="L-1", operator_id="OP-1"
    )
    
    # Valida o bloqueio arquitetural contra alteração retroativa
    with pytest.raises(FrozenInstanceError):
        entry.quantity_change = 20
def test_ledger_entry_validates_mathematical_invariant():
    with pytest.raises(ValueError, match="Invariante matemática violada"):
        LedgerEntry(
            id="TX-002", product_id="SKU-2", event_type="OUT",
            quantity_change=-5, quantity_before=10, quantity_after=10, # Deveria ser 5
            warehouse_id="WH-1", batch_code="L-2", operator_id="OP-1"
        )
def test_ledger_entry_requires_valid_event_type():
    with pytest.raises(ValueError, match="Tipo de evento inválido"):
        LedgerEntry(
            id="TX-003", product_id="SKU-3", event_type="MAGIC", # Tipo inexistente
            quantity_change=5, quantity_before=5, quantity_after=10,
            warehouse_id="WH-1", batch_code="L-3", operator_id="OP-1"
        )
KIPPE_HUNK
# 3. Semantic Validator & 4. AST Compile
kippe::step 2 ${TOTAL_STEPS} "Validating Semantics and Syntax..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
# 5. Regression Suite
kippe::step 3 ${TOTAL_STEPS} "Executing Core Regression Suite..."
kippe::test_execute_all
# 6. Architecture Scorecard
cat << "SCORECARD" > "${KIPPE_ROOT}/docs/checkpoints/ARCHITECTURE_SCORECARD-INV012.md"
# Architecture Scorecard - Kippe Platform
### Sprint: INV012 - Inventory Ledger

| Critério | Status | Detalhes |
| :--- | :--- | :--- |
| **Testes passando** | ✅ | GREEN. Validações de imutabilidade operacionais. |
| **Integridade Retroativa** | ✅ | Atributo \`frozen=True\` blinda Entidade contra adulteração em memória. |
| **Invariante Matemática** | ✅ | Cálculo \`before + change = after\` protegido nativamente. |
| **Gate C.3 (Logistics)** | ✅ | Base transacional estabelecida para o Livro-Razão logístico. |

SCORECARD
# 7. Checkpoint & 8. Manifest
kippe::checkpoint_create "050" "1.3.0-frozen" "INV012" "SUCCESS"
kippe::manifest_create "INV012" "C" "1.3.0-frozen" "SUCCESS" "INV013"
# 9 a 12. Atualização Automática de Estados e Sugestão (via Frozen Framework)
kippe::governance_sync \
    "C" "Inventory" \
    "2" "Profissional" \
    "C.3" "Logistics" \
    "INV012 (Inventory Ledger)" "INV013 — Inventory Snapshots" \
    "13/20 Sprints" "STABLE"
# 13. Commit Sugerido
echo -e "\n[AÇÃO REQUERIDA] Execute o commit para imutabilidade:"
echo -e 'git add -A && git commit -m "feat(inventory): implementa entidade imutavel e persistencia do livro-razao logistico (INV012)"'
exit 0
