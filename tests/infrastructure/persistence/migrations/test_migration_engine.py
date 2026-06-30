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
