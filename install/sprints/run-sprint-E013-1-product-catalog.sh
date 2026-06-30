#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM - PROGRAM E: WAREHOUSE & INVENTORY
# SPRINT E013.1: PRODUCT CATALOG FOUNDATION
# ============================================================

set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

source install/lib/bootstrap.sh
source install/lib/validation.sh
source install/lib/testing.sh

kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=3
kippe::banner_program "E" "E013.1" "Product Catalog Foundation"

# 1. Preparação da Estrutura do Novo Bounded Context
mkdir -p "${KIPPE_ROOT}/src/domain/catalog"
mkdir -p "${KIPPE_ROOT}/tests/domain/catalog"
mkdir -p "${KIPPE_ROOT}/src/infrastructure/persistence/memory"
touch "${KIPPE_ROOT}/src/domain/catalog/__init__.py"
touch "${KIPPE_ROOT}/tests/domain/catalog/__init__.py"

kippe::step 1 ${TOTAL_STEPS} "Deploying Catalog Domain (Entities & Ports)..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/catalog/product.py"
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Optional

@dataclass(frozen=True)
class Product:
    """
    Entidade Raiz do Bounded Context de Catálogo.
    Descreve a natureza estática do produto, agnóstica em relação ao estoque.
    """
    sku: str
    description: str
    brand: str
    category: str

class ProductCatalogRepository(ABC):
    """
    Porta de Saída (Outbound Port) para acesso ao Catálogo Central.
    Pode ser implementada em Memória, Base de Dados ou via API externa (ERP).
    """
    @abstractmethod
    def get_by_sku(self, sku: str) -> Optional[Product]:
        pass

    @abstractmethod
    def save(self, product: Product) -> None:
        pass
KIPPE_HUNK

# Exposição da API Pública do Catálogo
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/catalog/__init__.py"
from .product import Product, ProductCatalogRepository

__all__ = [
    "Product",
    "ProductCatalogRepository"
]
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Deploying Infrastructure Adapters (Memory & JSON)..."

# Mock em memória (Essencial para desbloquear a Audit Layer e testes isolados)
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/persistence/memory/product_catalog.py"
from typing import Optional, Dict
from src.domain.catalog.product import Product, ProductCatalogRepository

class InMemoryProductCatalog(ProductCatalogRepository):
    """Adaptador de Teste/Desenvolvimento para o Catálogo de Produtos."""
    def __init__(self):
        self._db: Dict[str, Product] = {
            "789609890001": Product(
                sku="789609890001",
                description="Detergente Ypê 500 ml",
                brand="Ypê",
                category="Limpeza"
            ),
            "000000000000": Product(
                sku="000000000000",
                description="Produto Genérico Não Registado",
                brand="Genérica",
                category="Diversos"
            )
        }

    def get_by_sku(self, sku: str) -> Optional[Product]:
        return self._db.get(sku)

    def save(self, product: Product) -> None:
        self._db[product.sku] = product
KIPPE_HUNK

# Adaptador JSON definitivo para o Catálogo
mkdir -p "${KIPPE_ROOT}/src/infrastructure/persistence/json"
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/infrastructure/persistence/json/product_catalog.py"
import os
import json
from typing import Optional, Dict
from src.domain.catalog.product import Product, ProductCatalogRepository

class JsonProductCatalog(ProductCatalogRepository):
    """Adaptador de Persistência Institucional para o Catálogo."""
    def __init__(self, file_path: str = "data/catalog/products.json"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            self._write_all({})

    def _read_all(self) -> Dict[str, dict]:
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_all(self, data: Dict[str, dict]) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_by_sku(self, sku: str) -> Optional[Product]:
        data = self._read_all()
        if sku not in data:
            return None
        p = data[sku]
        return Product(
            sku=p["sku"], description=p["description"],
            brand=p["brand"], category=p["category"]
        )

    def save(self, product: Product) -> None:
        data = self._read_all()
        data[product.sku] = {
            "sku": product.sku,
            "description": product.description,
            "brand": product.brand,
            "category": product.category
        }
        self._write_all(data)
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Verifying Syntax and Executing Platform Regression..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/domain/catalog/test_product_catalog.py"
from src.domain.catalog.product import Product
from src.infrastructure.persistence.memory.product_catalog import InMemoryProductCatalog

def test_catalog_retrieves_existing_product():
    repo = InMemoryProductCatalog()
    p = repo.get_by_sku("789609890001")
    assert p is not None
    assert p.description == "Detergente Ypê 500 ml"

def test_catalog_saves_new_product():
    repo = InMemoryProductCatalog()
    new_product = Product(sku="123", description="Novo Item", brand="Marca X", category="Extra")
    repo.save(new_product)
    
    loaded = repo.get_by_sku("123")
    assert loaded is not None
    assert loaded.description == "Novo Item"
KIPPE_HUNK

kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

# Registro de Estado e Manifesto
kippe::checkpoint_create "109" "1.5.0-platform" "E013.1" "SUCCESS"

kippe::governance_sync \
    "E" \
    "Warehouse & Inventory" \
    "4" \
    "Enterprise Foundation" \
    "E.8.1" \
    "Product Catalog Bounded Context" \
    "E013.1 (Catalog Foundation)" \
    "E014 — Command Pattern" \
    "13/20 Sprints" \
    "ACTIVE"

echo -e "\n[STATUS] Catálogo de Produtos implementado. As dependências da Audit Layer (E013) foram resolvidas!"
exit 0

