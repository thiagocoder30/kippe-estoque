#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E001.2: WAREHOUSE DOMAIN INVARIANTS
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
kippe::banner_program "E" "E001.2" "Warehouse Domain Invariants"

kippe::step 1 ${TOTAL_STEPS} "Implementing Aggregate Invariants in Topology Domain..."

# Implementando a validação DDD no Aggregate Root
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/topology.py"
from dataclasses import dataclass, field
from typing import List, Optional
from src.security.exceptions import BusinessRuleViolation

@dataclass
class StorageLocation:
    id: str
    name: str
    is_active: bool = True
    
    def disable(self): self.is_active = False
    def enable(self): self.is_active = True

@dataclass
class Warehouse:
    """
    Agregado Raiz com validação de invariantes no nascimento.
    Impede que o sistema entre em estado inválido por ID ou Nome ausente.
    """
    id: str
    name: str
    locations: List[StorageLocation] = field(default_factory=list)

    def __post_init__(self):
        if not self.id or not self.id.strip():
            raise ValueError("Warehouse deve possuir um código identificador.")
        if not self.name or not self.name.strip():
            raise ValueError("Warehouse deve possuir um nome institucional.")

    def add_location(self, location_id: str, name: str) -> StorageLocation:
        if any(loc.id == location_id for loc in self.locations):
            raise BusinessRuleViolation(f"Posição {location_id} já existe no armazém {self.id}.")
        
        loc = StorageLocation(id=location_id, name=name)
        self.locations.append(loc)
        return loc

    def get_location(self, location_id: str) -> Optional[StorageLocation]:
        for loc in self.locations:
            if loc.id == location_id:
                return loc
        return None
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Updating Test Suite & Validating Legacy Invariants..."

cat << "KIPPE_HUNK" >> "${KIPPE_ROOT}/tests/domain/warehouse/test_warehouse_topology.py"

def test_warehouse_must_have_id_and_name():
    with pytest.raises(ValueError, match="código identificador"):
        Warehouse(id="", name="Centro de Distribuição")
    
    with pytest.raises(ValueError, match="nome institucional"):
        Warehouse(id="CD-1", name="")
KIPPE_HUNK

kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Governança
kippe::checkpoint_create "091" "1.5.0-platform" "E001.2" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.1" \
    "Warehouse Topology" \
    "E001.2 (Domain Invariants)" \
    "E002 — Warehouse Persistence" \
    "2/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Invariantes do Domínio (E001.2) consolidadas e integradas ao legado."
exit 0

