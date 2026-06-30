from src.bootstrap import Bootstrap
from src.security.correlation import ExecutionContext
from src.domain.procurement.supplier import Supplier
import traceback
import sys

class SmokeTestEngine:
    """Executa um fluxo vital completo E2E para certificar o runtime respeitando os contratos do Domínio."""
    @staticmethod
    def execute() -> bool:
        try:
            app = Bootstrap(use_memory=True)
            ctx = ExecutionContext(user_id="SMOKE_TESTER")
            
            # 1. Configura Infra
            app.sup_repo.save(Supplier("SUP-SMOKE", "Corp", "001", "a@a.com", "ACTIVE"))
            
            # 2. Executa Use Case (Atravessando Decorator, Validator, Domain, Repo) - Retorna status DRAFT
            create_uc = app.get_create_po_use_case()
            create_uc.execute(ctx, "PO-SMK-01", "SUP-SMOKE", [{"sku": "ITM", "quantity": 10, "unit_price": 100.0}])
            
            # 3. Transição Estrita da Máquina de Estados (DRAFT -> SUBMITTED -> UNDER_APPROVAL)
            # Como a Application Layer não possui casos de uso dedicados para Submit/StartApproval, 
            # simulamos o fluxo de negócio via repositório para o Smoke Test respeitar as invariantes.
            order = app.po_repo.get_by_id("PO-SMK-01")
            order.submit()
            order.start_approval()
            app.po_repo.save(order)
            
            # 4. Executa Aprovação no Use Case
            approve_uc = app.get_approve_po_use_case()
            approve_uc.execute(ctx, "PO-SMK-01")
            
            # 5. Valida Estado Final
            saved = app.po_repo.get_by_id("PO-SMK-01")
            return saved is not None and saved.status == "APPROVED"
            
        except Exception as e:
            print(f"\\n[SMOKE TEST FATAL ERROR] {type(e).__name__}: {e}")
            traceback.print_exc(file=sys.stdout)
            return False
