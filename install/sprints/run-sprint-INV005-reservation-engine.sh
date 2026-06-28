#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM C: INVENTORY
# SPRINT INV005: INVENTORY RESERVATION ENGINE
# ============================================================
set -Eeuo pipefail
export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"
source install/lib/bootstrap.sh
source install/lib/testing.sh
source install/lib/validation.sh
kippe::init
kippe::init_environment
trap 'kippe::on_error ${LINENO}' ERR
TOTAL_STEPS=7
kippe::banner_program \
    "C" \
    "INV005" \
    "Inventory Reservation Engine"
kippe::step 1 ${TOTAL_STEPS} "Defining Reservation Entity (Domain Layer)..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/reservation.py"
from dataclasses import dataclass
from datetime import datetime
@dataclass
class Reservation:
    """
    Entidade: Reservation
    Garante o bloqueio lógico de estoque (Soft Allocation) para evitar rupturas de promessa.
    """
    id: str
    product_id: str
    amount: int
    operator_id: str
    status: str = "PENDING"  # PENDING, FULFILLED, CANCELLED
    created_at: str = ""
    def __post_init__(self):
        if not self.id or len(self.id.strip()) == 0:
            raise ValueError("ID da Reserva é obrigatório.")
        if not self.product_id or len(self.product_id.strip()) == 0:
            raise ValueError("ID do Produto é obrigatório para reserva.")
        if self.amount <= 0:
            raise ValueError("A quantidade reservada deve ser maior que zero.")
        if self.status not in ["PENDING", "FULFILLED", "CANCELLED"]:
            raise ValueError("Status de reserva inválido.")
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    def cancel(self) -> None:
        if self.status != "PENDING":
            raise ValueError(f"Não é possível cancelar uma reserva no status {self.status}.")
        self.status = "CANCELLED"
    def fulfill(self) -> None:
        if self.status != "PENDING":
            raise ValueError(f"Não é possível efetivar uma reserva no status {self.status}.")
        self.status = "FULFILLED"
KIPPE_HUNK
kippe::step 2 ${TOTAL_STEPS} "Refactoring Product Aggregate for Soft Allocation State..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/sprints/refactor_product_reservation.py"
import os
import sys
from pathlib import Path
if "KIPPE_ROOT" not in os.environ:
    sys.exit(1)
root = Path(os.environ["KIPPE_ROOT"])
product_path = root / "src/domain/product.py"
content = product_path.read_text(encoding="utf-8")
# Adiciona o campo reserved_quantity aos atributos do dataclass
if "reserved_quantity: int = 0" not in content:
    content = content.replace(
        "quantity: int = 0",
        "quantity: int = 0\n    reserved_quantity: int = 0"
    )
# Adiciona a propriedade de disponibilidade real (Físico - Reservado)
property_code = """
    @property
    def available_quantity(self) -> int:
        return self.quantity - self.reserved_quantity
"""
if "def available_quantity" not in content:
    content = content.replace("def __post_init__(self):", property_code + "\n    def __post_init__(self):")
# Atualiza a invariante de remoção para verificar se há estoque preso
if "return self.quantity == 0" in content:
    content = content.replace("return self.quantity == 0", "return self.quantity == 0 and self.reserved_quantity == 0")
product_path.write_text(content, encoding="utf-8")
KIPPE_HUNK
python3 "${KIPPE_ROOT}/install/sprints/refactor_product_reservation.py"
rm "${KIPPE_ROOT}/install/sprints/refactor_product_reservation.py"
kippe::step 3 ${TOTAL_STEPS} "Implementing Reservation Engine (Domain Service)..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/services/reservation_engine.py"
from src.domain.product import Product
from src.domain.reservation import Reservation
from src.domain.result import Result
import uuid
class ReservationEngine:
    """
    Domain Service: Orquestra o ciclo de vida das alocações de estoque.
    Previne venda a descoberto (Overselling) avaliando a quantidade disponível real.
    """
    
    @staticmethod
    def create_reservation(product: Product, amount: int, operator_id: str) -> Result[Reservation, str]:
        if product.status == "INATIVO":
            return Result.fail("Operação Rejeitada: Não é possível reservar produtos inativos.")
            
        if product.available_quantity < amount:
            return Result.fail(f"Estoque insuficiente. Físico: {product.quantity} | Disponível: {product.available_quantity} | Solicitado: {amount}")
            
        res_id = f"RES-{uuid.uuid4().hex[:8].upper()}"
        
        try:
            reservation = Reservation(id=res_id, product_id=product.id, amount=amount, operator_id=operator_id)
        except ValueError as e:
            return Result.fail(str(e))
            
        # Bloqueia a quantidade no agregado raiz
        product.reserved_quantity += amount
        return Result.ok(reservation)
    @staticmethod
    def cancel_reservation(product: Product, reservation: Reservation) -> Result[None, str]:
        if reservation.product_id != product.id:
            return Result.fail("A reserva não pertence a este produto.")
            
        try:
            reservation.cancel()
        except ValueError as e:
            return Result.fail(str(e))
            
        # Devolve a quantidade ao pool disponível
        product.reserved_quantity -= reservation.amount
        return Result.ok(None)
    @staticmethod
    def commit_reservation(product: Product, reservation: Reservation) -> Result[None, str]:
        """Efetiva a reserva, consumindo o estoque físico via política padrão do produto."""
        if reservation.product_id != product.id:
            return Result.fail("A reserva não pertence a este produto.")
            
        try:
            reservation.fulfill()
        except ValueError as e:
            return Result.fail(str(e))
            
        # Libera a trava lógica e realiza a baixa física real no Agregado
        product.reserved_quantity -= reservation.amount
        return product.remove_stock(reservation.amount)
KIPPE_HUNK
kippe::step 4 ${TOTAL_STEPS} "Expanding Persistence Layer for Soft Allocation Data..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/sprints/refactor_repo_reservation.py"
import os
import sys
from pathlib import Path
root = Path(os.environ["KIPPE_ROOT"])
repo_path = root / "src/interfaces/sqlite_repository.py"
content = repo_path.read_text(encoding="utf-8")
# Atualiza a tabela products para incluir reserved_quantity e cria a tabela reservations
migrations = """
            cursor = conn.execute("PRAGMA table_info(products)")
            columns = [info['name'] for info in cursor.fetchall()]
            if 'reserved_quantity' not in columns:
                conn.execute("ALTER TABLE products ADD COLUMN reserved_quantity INTEGER NOT NULL DEFAULT 0")
            conn.execute('''
                CREATE TABLE IF NOT EXISTS reservations (
                    id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    operator_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at DATETIME NOT NULL
                )
            ''')
"""
if "reserved_quantity INTEGER NOT NULL DEFAULT 0" not in content:
    content = content.replace(
        "cursor = conn.execute(\"PRAGMA table_info(products)\")",
        migrations
    )
# Atualiza o método save e get_by_id para contemplar reserved_quantity
content = content.replace(
    "quantity, unit_of_measure, status, category_id) VALUES (?, ?, ?, ?, ?, ?)",
    "quantity, unit_of_measure, status, category_id, reserved_quantity) VALUES (?, ?, ?, ?, ?, ?, ?)"
).replace(
    "category_id=excluded.category_id",
    "category_id=excluded.category_id, reserved_quantity=excluded.reserved_quantity"
).replace(
    "product.unit_of_measure, product.status, product.category_id))",
    "product.unit_of_measure, product.status, product.category_id, product.reserved_quantity))"
).replace(
    "category_id=prod_row['category_id']",
    "category_id=prod_row['category_id']"
)
# Adiciona ao get_by_id a injeção do reserved_quantity (bypassing the fact it might be missing in some lines, safely replacing the object construction)
content = content.replace(
    "category_id=prod_row['category_id'])",
    "category_id=prod_row['category_id'])\n            product.reserved_quantity = prod_row.get('reserved_quantity', 0)\n            return product"
).replace(
    "category_id=row['category_id'])",
    "category_id=row['category_id'])\n                products[-1].reserved_quantity = row.get('reserved_quantity', 0)"
)
repo_path.write_text(content, encoding="utf-8")
KIPPE_HUNK
python3 "${KIPPE_ROOT}/install/sprints/refactor_repo_reservation.py"
rm "${KIPPE_ROOT}/install/sprints/refactor_repo_reservation.py"
kippe::step 5 ${TOTAL_STEPS} "Writing Strict Tests for Reservation Operations..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/test_reservation_engine.py"
import pytest
from src.domain.product import Product
from src.domain.reservation import Reservation
from src.domain.services.reservation_engine import ReservationEngine
from datetime import datetime, timedelta
from src.domain.batch import Batch
def test_reservation_engine_blocks_overselling():
    p = Product(id="SKU-RES-1", name="Cadeira", quantity=10, reserved_quantity=8)
    
    # Restam apenas 2 fisicamente disponíveis
    res = ReservationEngine.create_reservation(p, 5, "OP-01")
    assert res.is_success is False
    assert "Estoque insuficiente" in res.error
    assert p.reserved_quantity == 8
def test_reservation_engine_successful_allocation():
    p = Product(id="SKU-RES-2", name="Mesa", quantity=10, reserved_quantity=0)
    
    res = ReservationEngine.create_reservation(p, 3, "OP-01")
    assert res.is_success is True
    assert p.reserved_quantity == 3
    assert p.available_quantity == 7
    
def test_reservation_cancellation_restores_availability():
    p = Product(id="SKU-RES-3", name="Estante", quantity=10, reserved_quantity=5)
    r = Reservation(id="R1", product_id="SKU-RES-3", amount=5, operator_id="OP")
    
    res = ReservationEngine.cancel_reservation(p, r)
    assert res.is_success is True
    assert r.status == "CANCELLED"
    assert p.reserved_quantity == 0
    assert p.available_quantity == 10
def test_reservation_commit_triggers_physical_removal():
    p = Product(id="SKU-RES-4", name="Sofa")
    amanha = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    p.batches["L1"] = Batch(code="L1", product_id="SKU-RES-4", quantity=10, expiration_date=amanha)
    p.quantity = 10
    
    res_alloc = ReservationEngine.create_reservation(p, 2, "OP-01")
    r = res_alloc.value
    
    res_commit = ReservationEngine.commit_reservation(p, r)
    assert res_commit.is_success is True
    assert r.status == "FULFILLED"
    
    # 2 foram removidos fisicamente, a trava foi solta.
    assert p.reserved_quantity == 0
    assert p.quantity == 8
KIPPE_HUNK
kippe::step 6 ${TOTAL_STEPS} "Executing Quality Gates & Core Regression Suite..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all
kippe::step 7 ${TOTAL_STEPS} "Generating Architecture Scorecard & Ledger Commit..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/docs/checkpoints/ARCHITECTURE_SCORECARD-INV005.md"
# Architecture Scorecard - Kippe Platform
### Sprint: INV005 - Inventory Reservation Engine

| Critério | Status | Detalhes / Métricas |
| :--- | :--- | :--- |
| **Testes passando** | ✅ | Suíte robustecida com operações de Soft Allocation. |
| **Contratos preservados** | ✅ | Product Aggregate mantido limpo; lógica em Domain Service. |
| **Cobertura documental** | ✅ | ROADMAP atualizado. |
| **ADR atualizado** | ✅ | Separação estrita entre Estoque Físico e Disponível. |
| **Gate impactado** | ❌ | Compiler e Preflight operacionais. |
| **Breaking changes** | ❌ | Assinaturas retrocompatíveis. |

KIPPE_HUNK
cat << "KIPPE_HUNK" > ESTADO_PROJETO.md
# 🌐 KIPPE PLATFORM: Institutional Retail Operations
## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 3 (Corporativo).
## 2. Status Executivo
* **Programa Atual:** PROGRAMA C (Inventory)
* **Gates Transpostos:**
  * [ GATE A - FOUNDATION READY ] ✅
  * [ GATE B - SECURITY READY ] ✅
  * [ GATE B.1 - ARCHITECTURE FREEZE ] ✅
  * [ GATE INFRA - RUNNER HARDENED ] ✅
* **Última Entrega:** Sprint INV005 (Inventory Reservation Engine)
## 3. Diretórios e Artefatos Essenciais
* `src/domain/services/reservation_engine.py` -> (Orquestrador de alocação de pedidos)
* `src/domain/reservation.py` -> (Entidade de retenção de intenção)
## 4. Próxima Ação Requerida
* **Sprint INV006 (Inventory Adjustment Engine):** Com as reservas garantindo a segurança das transações comerciais, precisamos construir o motor de Ajuste de Estoque, permitindo que a operação realize inventários rotativos (Physical Inventory), baixas por avaria e reconciliação contábil, tudo devidamente auditado no `transactions` log.
KIPPE_HUNK
kippe::checkpoint_create "029" "1.0.0" "INV005" "SUCCESS"
kippe::manifest_create "INV005" "C" "1.0.0" "SUCCESS" "INV006"
git add src/ tests/ install/sprints/ ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_INV005.json
git commit -m "feat(inventory): segrega logica de alocacao (Soft Allocation) no ReservationEngine (INV005)" || true
kippe::banner_finish
kippe::success "Reservation Engine successfully deployed. Soft Allocation prevents overselling."
exit 0
