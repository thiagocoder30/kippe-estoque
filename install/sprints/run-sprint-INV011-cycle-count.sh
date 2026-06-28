#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM C: INVENTORY
# SPRINT INV011: CYCLE COUNT ENGINE (Inventário Rotativo)
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
TOTAL_STEPS=4
kippe::banner_program "C" "INV011" "Cycle Count Engine"
kippe::step 1 ${TOTAL_STEPS} "Repository Maintenance (Gitignore & Artifact Cleanup)..."
# Sanetiza o repositório removendo logs rastreados acidentalmente
if [[ -f "${KIPPE_ROOT}/data/test_strict.log" ]]; then
    git rm --cached "${KIPPE_ROOT}/data/test_strict.log" 2>/dev/null || true
fi
# Assegura que logs e bancos de dados SQLite transientes sejam ignorados
if ! grep -q "data/\*.log" "${KIPPE_ROOT}/.gitignore" 2>/dev/null; then
    echo "data/*.log" >> "${KIPPE_ROOT}/.gitignore"
    echo "data/*.db" >> "${KIPPE_ROOT}/.gitignore"
    echo "data/*.db-journal" >> "${KIPPE_ROOT}/.gitignore"
    echo "__pycache__/" >> "${KIPPE_ROOT}/.gitignore"
fi
kippe::step 2 ${TOTAL_STEPS} "Designing Domain Entities & Services (Cycle Count)..."
# Criação da Entidade de Tarefa de Contagem
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/cycle_count.py"
from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
@dataclass
class CycleCountTask:
    """
    Entidade: CycleCountTask
    Representa uma ordem de serviço para inventário rotativo geográfico.
    """
    id: str
    warehouse_id: str
    operator_id: str
    location_filter: str = "GLOBAL"  # Ex: Corredor A, Setor Frios
    status: str = "OPEN"             # OPEN, IN_PROGRESS, COMPLETED, APPROVED
    counted_items: Dict[str, int] = field(default_factory=dict)  # batch_code -> quantidade_contada
    created_at: str = ""
    approved_by: Optional[str] = None
    def __post_init__(self):
        if not self.id:
            raise ValueError("ID da Tarefa de Contagem é obrigatório.")
        if not self.warehouse_id:
            raise ValueError("Armazém alvo é obrigatório.")
        if not self.operator_id:
            raise ValueError("ID do Operador responsável pela contagem é obrigatório.")
        if self.status not in ["OPEN", "IN_PROGRESS", "COMPLETED", "APPROVED"]:
            raise ValueError("Status da Tarefa de Contagem inválido.")
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
KIPPE_HUNK
# Criação do Motor de Inventário Rotativo
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/src/domain/services/cycle_count_engine.py"
from typing import List
from src.domain.product import Product
from src.domain.cycle_count import CycleCountTask
from src.domain.result import Result
from src.domain.services.inventory_adjustment_engine import InventoryAdjustmentEngine
class CycleCountEngine:
    """
    Domain Service: CycleCountEngine
    Gerencia a descoberta de divergências físicas.
    Delega a aplicação de correções ao InventoryAdjustmentEngine mediante aprovação.
    """
    @staticmethod
    def register_count(task: CycleCountTask, batch_code: str, quantity: int) -> Result[None, str]:
        if task.status not in ["OPEN", "IN_PROGRESS"]:
            return Result.fail(f"Não é possível registrar contagens em uma tarefa com status {task.status}.")
        if quantity < 0:
            return Result.fail("A quantidade contada não pode ser negativa.")
            
        task.status = "IN_PROGRESS"
        task.counted_items[batch_code] = quantity
        return Result.ok(None)
    @staticmethod
    def complete_task(task: CycleCountTask) -> Result[None, str]:
        if task.status != "IN_PROGRESS":
            return Result.fail("Apenas tarefas EM ANDAMENTO podem ser marcadas como concluídas.")
        task.status = "COMPLETED"
        return Result.ok(None)
    @staticmethod
    def approve_and_reconcile(task: CycleCountTask, products: List[Product], approver_id: str) -> Result[None, str]:
        if task.status != "COMPLETED":
            return Result.fail("A tarefa deve estar CONCLUÍDA antes da aprovação gerencial.")
        if not approver_id:
            return Result.fail("O ID do Aprovador é obrigatório para trilha de auditoria.")
        # Reconciliação Física vs Sistêmica
        for product in products:
            for batch_code, counted_qty in task.counted_items.items():
                if batch_code in product.batches:
                    system_qty = product.batches[batch_code].quantity
                    difference = counted_qty - system_qty
                    
                    if difference != 0:
                        reason = "SOBRA" if difference > 0 else "PERDA"
                        
                        # Delegação arquitetural para o motor de ajustes consolidado na INV010
                        adj_res = InventoryAdjustmentEngine.execute_adjustment(
                            product=product,
                            amount=difference,
                            reason=reason,
                            operator_id=approver_id,
                            warehouse_id=task.warehouse_id,
                            batch_code=batch_code
                        )
                        if not adj_res.is_success:
                            return Result.fail(f"Falha de conciliação no lote {batch_code}: {adj_res.error}")
        task.status = "APPROVED"
        task.approved_by = approver_id
        return Result.ok(None)
KIPPE_HUNK
# Criação da suíte de testes do Cycle Count
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/tests/test_cycle_count.py"
import pytest
from src.domain.product import Product
from src.domain.batch import Batch
from src.domain.cycle_count import CycleCountTask
from src.domain.services.cycle_count_engine import CycleCountEngine
def test_cycle_count_perfect_match():
    p = Product(id="SKU-CC-1", name="Arroz")
    p.batches["L-100"] = Batch(code="L-100", product_id="SKU-CC-1", quantity=50, expiration_date="2030-01-01", warehouse_id="WH-1")
    p.quantity = 50
    
    task = CycleCountTask(id="CC-001", warehouse_id="WH-1", operator_id="OP-01")
    
    # Registra contagem exata
    res1 = CycleCountEngine.register_count(task, "L-100", 50)
    assert res1.is_success is True
    
    res2 = CycleCountEngine.complete_task(task)
    assert res2.is_success is True
    
    res3 = CycleCountEngine.approve_and_reconcile(task, [p], "MGR-01")
    assert res3.is_success is True
    assert p.quantity == 50 # Nenhuma alteração foi necessária
def test_cycle_count_with_shortage_delegates_to_adjustment():
    p = Product(id="SKU-CC-2", name="Feijão")
    p.batches["L-200"] = Batch(code="L-200", product_id="SKU-CC-2", quantity=30, expiration_date="2030-01-01", warehouse_id="WH-1")
    p.quantity = 30
    
    task = CycleCountTask(id="CC-002", warehouse_id="WH-1", operator_id="OP-01")
    
    # Registra falta física (achou apenas 25)
    CycleCountEngine.register_count(task, "L-200", 25)
    CycleCountEngine.complete_task(task)
    
    res = CycleCountEngine.approve_and_reconcile(task, [p], "MGR-01")
    assert res.is_success is True
    assert task.status == "APPROVED"
    # O InventoryAdjustmentEngine deve ter debitado 5
    assert p.batches["L-200"].quantity == 25
    assert p.quantity == 25
def test_cycle_count_with_surplus_delegates_to_adjustment():
    p = Product(id="SKU-CC-3", name="Macarrão")
    p.batches["L-300"] = Batch(code="L-300", product_id="SKU-CC-3", quantity=10, expiration_date="2030-01-01", warehouse_id="WH-1")
    p.quantity = 10
    
    task = CycleCountTask(id="CC-003", warehouse_id="WH-1", operator_id="OP-01")
    
    # Registra sobra física (achou 15)
    CycleCountEngine.register_count(task, "L-300", 15)
    CycleCountEngine.complete_task(task)
    
    CycleCountEngine.approve_and_reconcile(task, [p], "MGR-01")
    assert p.batches["L-300"].quantity == 15
    assert p.quantity == 15
def test_cycle_count_rejects_unauthorized_closure():
    task = CycleCountTask(id="CC-004", warehouse_id="WH-1", operator_id="OP-01")
    
    # Tenta aprovar uma tarefa que está OPEN (não completada)
    res = CycleCountEngine.approve_and_reconcile(task, [], "MGR-01")
    assert res.is_success is False
    assert "A tarefa deve estar CONCLUÍDA antes da aprovação" in res.error
KIPPE_HUNK
# 3. Semantic Validator & 4. AST Compile
kippe::step 3 ${TOTAL_STEPS} "Validating Semantics and Syntax..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
# 5. Regression Suite
kippe::step 4 ${TOTAL_STEPS} "Executing Core Regression Suite..."
kippe::test_execute_all
# 6. Architecture Scorecard
cat << "SCORECARD" > "${KIPPE_ROOT}/docs/checkpoints/ARCHITECTURE_SCORECARD-INV011.md"
# Architecture Scorecard - Kippe Platform
### Sprint: INV011 - Cycle Count Engine

| Critério | Status | Detalhes |
| :--- | :--- | :--- |
| **Testes passando** | ✅ | GREEN. Faltas, sobras e auditoria testadas. |
| **Delegação de Domínio** | ✅ | Respeito estrito ao SRP. Mutações delegadas ao \`InventoryAdjustmentEngine\`. |
| **Auditoria** | ✅ | \`operator_id\` e \`approver_id\` exigidos para conciliação sistêmica. |
| **Gate C.3 (Logistics)** | ✅ | Capacidade de auditoria rotativa de prateleiras estabelecida. |

SCORECARD
# 7. Checkpoint & 8. Manifest
kippe::checkpoint_create "049" "1.3.0-frozen" "INV011" "SUCCESS"
kippe::manifest_create "INV011" "C" "1.3.0-frozen" "SUCCESS" "INV012"
# 9 a 12. Atualização Automática de Estados e Sugestão (via Frozen Framework)
kippe::governance_sync \
    "C" "Inventory" \
    "2" "Profissional" \
    "C.3" "Logistics" \
    "INV011 (Cycle Count Engine)" "INV012 — Inventory Ledger" \
    "12/20 Sprints" "STABLE"
# 13. Commit Sugerido
echo -e "\n[AÇÃO REQUERIDA] Execute os comandos abaixo para consolidar a sprint:"
echo -e "git add .gitignore data/ || true"
echo -e 'git commit -m "chore(repo): ignora e remove artefatos de logs transientes gerados por testes"'
echo -e "git add -A"
echo -e 'git commit -m "feat(inventory): implementa motor de inventario rotativo (Cycle Count) integrado aos ajustes fisicos (INV011)"'
exit 0
