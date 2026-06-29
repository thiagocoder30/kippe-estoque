#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM D: PROCUREMENT
# SPRINT D001: SUPPLIER FOUNDATION & CONTRACTS
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

# 1. Carregamento do Framework
source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

# Blindagem de Infraestrutura (Fail-Fast)
for fn in kippe::init kippe::validate_script_syntax kippe::test_execute_all kippe::checkpoint_create; do
    if ! declare -F "$fn" >/dev/null; then
        echo "[FATAL] Framework function missing: $fn. O script foi interrompido."
        exit 1
    fi
done

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=3
kippe::banner_program "D" "D001" "Supplier Foundation & Contracts"

# Preparação de Bounded Context (Encapsulamento Físico)
mkdir -p "${KIPPE_ROOT}/src/domain/procurement"
mkdir -p "${KIPPE_ROOT}/tests/procurement"
touch "${KIPPE_ROOT}/src/domain/procurement/__init__.py"
touch "${KIPPE_ROOT}/tests/procurement/__init__.py"

kippe::step 1 ${TOTAL_STEPS} "Deploying Supplier Entity (Strict Contract Foundation)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/procurement/supplier.py"
from dataclasses import dataclass
from typing import Any
import re

@dataclass
class Supplier:
    """
    Entidade Canônica: Supplier (Fornecedor)
    Módulo D: Procurement.
    Nasce sob a nova doutrina Contract-First: Validação estrita no construtor
    sem dependência de persistência ou adaptadores legados.
    """
    id: str
    corporate_name: str
    tax_id: str  # CNPJ/Tax Number corporativo
    email: str
    status: str = "ACTIVE"
    lead_time_days: int = 0

    def __post_init__(self):
        # Validação Hierárquica Estrita
        if not self.id or not str(self.id).strip():
            raise ValueError("O ID do fornecedor é obrigatório.")
            
        if not self.corporate_name or not str(self.corporate_name).strip():
            raise ValueError("A Razão Social (corporate_name) é obrigatória.")
            
        if not self.tax_id or not str(self.tax_id).strip():
            raise ValueError("O Documento Fiscal (tax_id) é obrigatório.")
            
        if not self.email or "@" not in str(self.email):
            raise ValueError("O endereço de email fornecido é inválido.")
            
        if self.lead_time_days < 0:
            raise ValueError("O lead time logístico não pode ser negativo.")
            
        if self.status not in ["ACTIVE", "INACTIVE", "BLOCKED"]:
            raise ValueError("Status do fornecedor inválido.")
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Domain Contract Test Suite (Test-Driven Validation)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/procurement/test_supplier_entity.py"
import pytest
from src.domain.procurement.supplier import Supplier

def test_supplier_canonical_creation_success():
    supplier = Supplier(
        id="SUP-001",
        corporate_name="Tech Distribuidora S.A.",
        tax_id="63.269.720/0001-77",
        email="contato@techdistribuidora.com.br",
        lead_time_days=5
    )
    assert supplier.id == "SUP-001"
    assert supplier.status == "ACTIVE"
    assert supplier.lead_time_days == 5

def test_supplier_enforces_required_fields():
    with pytest.raises(ValueError, match="ID do fornecedor é obrigatório"):
        Supplier(id="", corporate_name="Fornecedor X", tax_id="123", email="x@x.com")
        
    with pytest.raises(ValueError, match="Razão Social \\(corporate_name\\) é obrigatória"):
        Supplier(id="SUP-002", corporate_name="", tax_id="123", email="x@x.com")
        
    with pytest.raises(ValueError, match="Documento Fiscal \\(tax_id\\) é obrigatório"):
        Supplier(id="SUP-003", corporate_name="Fornecedor Y", tax_id="", email="y@y.com")

def test_supplier_enforces_valid_email():
    with pytest.raises(ValueError, match="endereço de email fornecido é inválido"):
        Supplier(id="SUP-004", corporate_name="Fornecedor W", tax_id="123", email="email-invalido.com")

def test_supplier_enforces_positive_lead_time():
    with pytest.raises(ValueError, match="lead time logístico não pode ser negativo"):
        Supplier(id="SUP-005", corporate_name="Fornecedor Z", tax_id="123", email="z@z.com", lead_time_days=-2)

def test_supplier_enforces_valid_status():
    with pytest.raises(ValueError, match="Status do fornecedor inválido"):
        Supplier(id="SUP-006", corporate_name="Fornecedor H", tax_id="123", email="h@h.com", status="BANNED")
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Base Contracts (Domain Lock)..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado Inaugural do Programa D
kippe::checkpoint_create "065" "1.4.0-procurement" "D001" "SUCCESS"

# Atualização da Governança para o Novo Programa
kippe::governance_sync \
    "D" \
    "Procurement" \
    "4" \
    "Enterprise Foundation" \
    "D.1" \
    "Supplier Identity" \
    "D001 (Supplier Contracts)" \
    "D002 — Purchase Order Aggregate" \
    "1/20 Sprints" \
    "STABLE"

echo -e "\n[STATUS] Fundação de Procurement (D001) estabelecida com disciplina Contract-First."
exit 0

