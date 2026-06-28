#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM C: INVENTORY
# SPRINT INV013: INVENTORY SNAPSHOTS (State Restoration)
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
kippe::banner_program "C" "INV013" "Inventory Snapshots"
# 2. SafeRefactor (Domain Evolution)
kippe::step 1 ${TOTAL_STEPS} "Applying Domain Mutations: Snapshot Engine & Persistence..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/snapshot.py"
from dataclasses import dataclass, field
from datetime import datetime
@dataclass(frozen=True)
class InventorySnapshot:
    """
    Entidade: InventorySnapshot
    Captura imutável do estado consolidado do inventário em um instante T.
    """
    id: str
    payload: str  # Representação JSON estrita do estado (Aggregate Roots + Batches)
    created_by: str = "SYSTEM"
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    def __post_init__(self):
        if not self.id:
            raise ValueError("O identificador do Snapshot é obrigatório.")
        if not self.payload:
            raise ValueError("O payload do Snapshot não pode ser vazio.")
KIPPE_HUNK
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/services/snapshot_engine.py"
import json
from typing import List, Dict, Any
from src.domain.product import Product
from src.domain.batch import Batch
from src.domain.snapshot import InventorySnapshot
class SnapshotEngine:
    """
    Domain Service: Snapshot Engine
    Gerador e restaurador de estados para auditoria e performance.
    """
    @staticmethod
    def capture(snapshot_id: str, products: List[Product], operator_id: str = "SYSTEM") -> InventorySnapshot:
        data = []
        for p in products:
            batches_data = {k: v.__dict__ for k, v in p.batches.items()}
            p_data = {
                "id": p.id,
                "name": p.name,
                "quantity": p.quantity,
                "reserved_quantity": p.reserved_quantity,
                "unit_of_measure": p.unit_of_measure,
                "status": p.status,
                "category_id": p.category_id,
                "batches": batches_data
            }
            data.append(p_data)
        
        return InventorySnapshot(
            id=snapshot_id,
            payload=json.dumps(data),
            created_by=operator_id
        )
    @staticmethod
    def restore(snapshot: InventorySnapshot) -> List[Product]:
        try:
            data = json.loads(snapshot.payload)
        except json.JSONDecodeError:
            raise ValueError("Payload de Snapshot corrompido ou inválido.")
        restored_products = []
        for p_data in data:
            batches = {}
            for b_code, b_info in p_data.get("batches", {}).items():
                batches[b_code] = Batch(**b_info)
            
            prod = Product(
                id=p_data["id"],
                name=p_data["name"],
                quantity=p_data["quantity"],
                reserved_quantity=p_data.get("reserved_quantity", 0),
                unit_of_measure=p_data.get("unit_of_measure", "un"),
                status=p_data.get("status", "ATIVO"),
                category_id=p_data.get("category_id")
            )
            prod.batches = batches
            restored_products.append(prod)
            
        return restored_products
KIPPE_HUNK
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/interfaces/sqlite_snapshot_repository.py"
import sqlite3
from typing import Optional
from src.domain.snapshot import InventorySnapshot
class SQLiteSnapshotRepository:
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
                CREATE TABLE IF NOT EXISTS inventory_snapshots (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            ''')
            conn.commit()
    def save(self, snapshot: InventorySnapshot) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO inventory_snapshots (id, payload, created_by, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (snapshot.id, snapshot.payload, snapshot.created_by, snapshot.timestamp))
            conn.commit()
    def get_by_id(self, snapshot_id: str) -> Optional[InventorySnapshot]:
        with self._get_connection() as conn:
            row = conn.execute('SELECT * FROM inventory_snapshots WHERE id = ?', (snapshot_id,)).fetchone()
            if not row: return None
            r_dict = dict(row)
            return InventorySnapshot(
                id=r_dict['id'],
                payload=r_dict['payload'],
                created_by=r_dict['created_by'],
                timestamp=r_dict['timestamp']
            )
KIPPE_HUNK
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/test_inventory_snapshots.py"
import pytest
from src.domain.product import Product
from src.domain.batch import Batch
from src.domain.services.snapshot_engine import SnapshotEngine
def test_snapshot_capture_and_restore_integrity():
    # Prepara o estado inicial
    p1 = Product(id="SKU-SNAP-1", name="Placa Mae", quantity=10)
    p1.batches["L-1"] = Batch(code="L-1", product_id="SKU-SNAP-1", quantity=10, expiration_date="2030-12-31")
    
    p2 = Product(id="SKU-SNAP-2", name="Memoria RAM", quantity=20, reserved_quantity=5)
    p2.batches["L-2"] = Batch(code="L-2", product_id="SKU-SNAP-2", quantity=20, expiration_date="2030-12-31", warehouse_id="WH-2")
    
    state = [p1, p2]
    
    # 1. Executa Captura
    snapshot = SnapshotEngine.capture(snapshot_id="SNAP-TEST-001", products=state, operator_id="AUDITOR-99")
    
    assert snapshot.id == "SNAP-TEST-001"
    assert snapshot.created_by == "AUDITOR-99"
    assert "Placa Mae" in snapshot.payload
    assert "Memoria RAM" in snapshot.payload
    
    # 2. Executa Restauração
    restored_state = SnapshotEngine.restore(snapshot)
    
    # 3. Valida Invariantes de Reconstrução
    assert len(restored_state) == 2
    
    r_p1 = next(p for p in restored_state if p.id == "SKU-SNAP-1")
    assert r_p1.quantity == 10
    assert r_p1.batches["L-1"].expiration_date == "2030-12-31"
    
    r_p2 = next(p for p in restored_state if p.id == "SKU-SNAP-2")
    assert r_p2.reserved_quantity == 5
    assert r_p2.batches["L-2"].warehouse_id == "WH-2"
KIPPE_HUNK
# 3. Semantic Validator & 4. AST Compile
kippe::step 2 ${TOTAL_STEPS} "Validating Semantics and Syntax..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
# 5. Regression Suite
kippe::step 3 ${TOTAL_STEPS} "Executing Core Regression Suite..."
kippe::test_execute_all
# 6. Architecture Scorecard
cat << "SCORECARD" > "${KIPPE_ROOT}/docs/checkpoints/ARCHITECTURE_SCORECARD-INV013.md"
# Architecture Scorecard - Kippe Platform
### Sprint: INV013 - Inventory Snapshots

| Critério | Status | Detalhes |
| :--- | :--- | :--- |
| **Testes passando** | ✅ | GREEN. Garantia de captura e restauração 1:1 sem perda de dados. |
| **Invariante de Imutabilidade** | ✅ | A entidade \`InventorySnapshot\` usa dataclass frozen para isolar estado. |
| **Performance** | ✅ | Possibilita restaurar estado T sem iterar todo o \`Ledger\`. |
| **Gate C.3 (Logistics)** | ✅ | Auditoria contábil solidificada. |

SCORECARD
# 7. Checkpoint & 8. Manifest
kippe::checkpoint_create "051" "1.3.0-frozen" "INV013" "SUCCESS"
kippe::manifest_create "INV013" "C" "1.3.0-frozen" "SUCCESS" "INV014"
# 9 a 12. Atualização Automática de Estados e Sugestão
kippe::governance_sync \
    "C" "Inventory" \
    "2" "Profissional" \
    "C.3" "Logistics" \
    "INV013 (Inventory Snapshots)" "INV014 — Warehouse Analytics" \
    "14/20 Sprints" "STABLE"
# 13. Commit Sugerido (Saída no console)
echo -e "\n[AÇÃO REQUERIDA] Execute o commit para imutabilidade:"
echo -e 'git add -A && git commit -m "feat(inventory): implementa motor de snapshots para captura e restauracao de estado consolidado (INV013)"'
exit 0
