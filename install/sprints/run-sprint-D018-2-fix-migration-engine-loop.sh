#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D018.2: FIX MIGRATION ENGINE INFINITE LOOP
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

# 1. Carregamento do Framework
source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=2
kippe::banner_program "D" "D018.2" "Fix Migration Engine Infinite Loop"

kippe::step 1 ${TOTAL_STEPS} "Deploying Cycle Detection to Migration Engine..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/persistence/migrations/engine.py"
from typing import Dict, Any, Callable

class MigrationEngine:
    """
    Motor de Migração (Upcasting) para a Camada de Infraestrutura.
    Intercepta dados desserializados brutos e aplica transformações sequenciais.
    Implementa proteção DAG (Grafo Direcionado Acíclico) contra loops infinitos.
    """
    def __init__(self):
        self._upcasters: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    def register_upcaster(self, from_version: str, upcaster_func: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self._upcasters[from_version] = upcaster_func

    def migrate(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        current_version = raw_data.get("schema_version", "1.0")
        migrated_data = raw_data.copy()
        visited = set()
        
        while current_version in self._upcasters:
            # Proteção contra Estagnação de Estado e Ciclos (Infinite Loop)
            if current_version in visited:
                raise RuntimeError(f"Ciclo de migração detectado na versão {current_version}.")
            visited.add(current_version)
            
            upcaster = self._upcasters[current_version]
            migrated_data = upcaster(migrated_data)
            current_version = migrated_data.get("schema_version")
            
            if not current_version:
                raise RuntimeError("Falha no Upcaster: schema_version não atualizado na transformação.")
                
        return migrated_data
KIPPE_HUNK

# Atualizando o teste para esperar a nova mensagem de proteção contra ciclos
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/infrastructure/persistence/migrations/test_migration_engine.py"
import pytest
from src.infrastructure.persistence.migrations.engine import MigrationEngine
from src.infrastructure.persistence.migrations.upcasters import purchase_order_v1_0_to_v1_1

def test_migration_engine_upcasts_v1_to_v1_1():
    engine = MigrationEngine()
    engine.register_upcaster("1.0", purchase_order_v1_0_to_v1_1)
    
    legacy_payload = {
        "schema_version": "1.0",
        "id": "PO-LEGACY-001",
        "supplier_id": "SUP-1",
        "issue_date": "2023-01-01",
        "status": "DRAFT",
        "items": []
    }
    
    migrated = engine.migrate(legacy_payload)
    
    assert migrated["schema_version"] == "1.1"
    assert "tags" in migrated
    assert migrated["tags"] == ["migrated_from_v1.0"]
    assert migrated["id"] == "PO-LEGACY-001"

def test_migration_engine_chains_multiple_versions():
    engine = MigrationEngine()
    engine.register_upcaster("1.0", lambda data: {**data, "schema_version": "2.0", "v2_field": True})
    engine.register_upcaster("2.0", lambda data: {**data, "schema_version": "3.0", "v3_field": "ok"})
    
    raw = {"schema_version": "1.0", "id": "TEST"}
    final = engine.migrate(raw)
    
    assert final["schema_version"] == "3.0"
    assert final["v2_field"] is True
    assert final["v3_field"] == "ok"

def test_migration_engine_fails_safely_on_broken_upcaster_loop():
    engine = MigrationEngine()
    # Upcaster defeituoso que esquece de atualizar a versão (causaria loop infinito)
    engine.register_upcaster("1.0", lambda data: {**data, "new_field": True})
    
    with pytest.raises(RuntimeError, match="Ciclo de migração detectado"):
        engine.migrate({"schema_version": "1.0"})
        
def test_migration_engine_fails_safely_on_missing_version():
    engine = MigrationEngine()
    # Upcaster defeituoso que apaga a versão
    engine.register_upcaster("1.0", lambda data: {"outro_campo": "vazio"})
    
    with pytest.raises(RuntimeError, match="não atualizado na transformação"):
        engine.migrate({"schema_version": "1.0"})
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Verifying Syntax and Executing Full Regression Suite..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "084" "1.4.0-procurement" "D018.2" "SUCCESS"

kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D018.2 (Migration Loop Fix)" \
    "D019 — Resilience & Fault Tolerance" \
    "18/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Migration Engine Loop Fix (D018.2) protegido com sucesso via DAG."
exit 0

