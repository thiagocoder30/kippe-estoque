#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E001: WAREHOUSE TOPOLOGY (LEAN MODEL)
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

TOTAL_STEPS=3
kippe::banner_program "E" "E001" "Warehouse Topology (Lean Model)"

# Preparação de Diretórios
mkdir -p "${KIPPE_ROOT}/src/domain/warehouse"
mkdir -p "${KIPPE_ROOT}/tests/domain/warehouse"
touch "${KIPPE_ROOT}/src/domain/warehouse/__init__.py"
touch "${KIPPE_ROOT}/tests/domain/warehouse/__init__.py"

kippe::step 1 ${TOTAL_STEPS} "Deploying Lean Warehouse Topology (Domain Layer)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/topology.py"
from dataclasses import dataclass, field
from typing import List, Optional
from src.security.exceptions import BusinessRuleViolation

@dataclass
class StorageLocation:
    """
    Representa uma posição física real no depósito.
    Modelo Lean: Ignora volumetria 3D e foca na identificação visual direta
    (Ex: Estante A, Chão Palete Sul).
    """
    id: str
    name: str
    is_active: bool = True
    
    def disable(self):
        self.is_active = False
        
    def enable(self):
        self.is_active = True

@dataclass
class Warehouse:
    """
    Agregado Raiz da Topologia de Armazém.
    Representa o espaço físico delimitado que contém posições de estoque.
    """
    id: str
    name: str
    locations: List[StorageLocation] = field(default_factory=list)

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

kippe::step 2 ${TOTAL_STEPS} "Deploying Topology Repository Interfaces..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/warehouse/repository.py"
from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.warehouse.topology import Warehouse

class WarehouseRepository(ABC):
    """Porta de saída para a persistência da topologia do armazém."""
    @abstractmethod
    def save(self, warehouse: Warehouse) -> None:
        pass

    @abstractmethod
    def get_by_id(self, warehouse_id: str) -> Optional[Warehouse]:
        pass

    @abstractmethod
    def get_all(self) -> List[Warehouse]:
        pass
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Deploying Domain Unit Tests for Lean Topology..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/domain/warehouse/test_warehouse_topology.py"
import pytest
from src.domain.warehouse.topology import Warehouse, StorageLocation
from src.security.exceptions import BusinessRuleViolation

def test_create_warehouse_and_add_lean_locations():
    wh = Warehouse(id="WH-MAIN", name="Depósito Principal")
    
    # Baseado na realidade visual avaliada
    wh.add_location("CHAO-DIR", "Paletes Chão Lado Direito")
    wh.add_location("EST-B", "Estante Metálica B")
    
    assert len(wh.locations) == 2
    assert wh.get_location("CHAO-DIR").is_active is True

def test_prevent_duplicate_locations():
    wh = Warehouse(id="WH-MAIN", name="Depósito Principal")
    wh.add_location("LOC-1", "Posição Única")
    
    with pytest.raises(BusinessRuleViolation, match="já existe"):
        wh.add_location("LOC-1", "Posição Duplicada")

def test_disable_storage_location():
    wh = Warehouse(id="WH-MAIN", name="Depósito Principal")
    loc = wh.add_location("LOC-MAINT", "Posição Bloqueada")
    
    loc.disable()
    assert loc.is_active is False
    
    loc.enable()
    assert loc.is_active is True
KIPPE_HUNK

kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "089" "1.5.0-platform" "E001" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.1" \
    "Warehouse Topology" \
    "E001 (Warehouse Topology Lean)" \
    "E002 — Warehouse Persistence" \
    "1/20 Sprints" \
    "ACTIVE"

echo -e "\n[STATUS] Domain Layer para Warehouse Topology (Modelo Lean) consolidada com sucesso."
exit 0

