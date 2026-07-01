import os
from src.infrastructure.release.certification import ProductionCertificationEngine, ReleaseBuilder, EnvironmentValidator

def test_environment_validator_passes():
    # Em um ambiente pytest limpo e executando, isto tem de ser verdadeiro
    assert EnvironmentValidator.validate(".") is True

def test_certification_engine_evaluates_system(tmp_path):
    engine = ProductionCertificationEngine(str(tmp_path))
    result = engine.run_certification()
    
    # O diretório tmp_path está vazio, a arquitetura deve falhar, logo is_ready = False
    assert result.is_ready is False
    assert result.checks["Environment"] is True # Mesmo num tmp_path, temos python e permissão de escrita

def test_release_builder_generates_manifest_and_version(tmp_path):
    engine = ProductionCertificationEngine(str(tmp_path))
    result = engine.run_certification()
    
    builder = ReleaseBuilder(str(tmp_path))
    manifest = builder.build(result)
    
    release_dir = tmp_path / "release"
    assert release_dir.exists()
    assert (release_dir / "RELEASE_MANIFEST.json").exists()
    assert (release_dir / "VERSION").exists()
    assert (release_dir / "snapshot" / "release_manifest.json").exists()
    
    assert manifest["KIPPE_PLATFORM"] == "Warehouse & Inventory"
    assert manifest["Release"] == "FAILED" # Consequência do tmp_path estar vazio
